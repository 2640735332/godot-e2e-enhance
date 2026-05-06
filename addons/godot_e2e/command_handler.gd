const JsonSerializer = preload("json_serializer.gd")

var _server


func _init(server) -> void:
	_server = server


func execute(cmd: Dictionary) -> Dictionary:
	var action: String = cmd.get("action", "")
	var id = cmd.get("id", null)

	match action:
		"node_exists":
			return _cmd_node_exists(cmd, id)
		"get_property":
			return _cmd_get_property(cmd, id)
		"set_property":
			return _cmd_set_property(cmd, id)
		"call_method":
			return _cmd_call_method(cmd, id)
		"find_by_group":
			return _cmd_find_by_group(cmd, id)
		"query_nodes":
			return _cmd_query_nodes(cmd, id)
		"get_tree":
			return _cmd_get_tree(cmd, id)
		"batch":
			return _cmd_batch(cmd, id)
		"input_key":
			return _cmd_input_key(cmd, id)
		"input_action":
			return _cmd_input_action(cmd, id)
		"input_mouse_button":
			return _cmd_input_mouse_button(cmd, id)
		"input_mouse_motion":
			return _cmd_input_mouse_motion(cmd, id)
		"click_node":
			return _cmd_click_node(cmd, id)
		"wait_process_frames":
			return _cmd_wait_process_frames(cmd, id)
		"wait_physics_frames":
			return _cmd_wait_physics_frames(cmd, id)
		"wait_seconds":
			return _cmd_wait_seconds(cmd, id)
		"wait_for_node":
			return _cmd_wait_for_node(cmd, id)
		"wait_for_signal":
			return _cmd_wait_for_signal(cmd, id)
		"wait_for_property":
			return _cmd_wait_for_property(cmd, id)
		"get_scene":
			return _cmd_get_scene(cmd, id)
		"change_scene":
			return _cmd_change_scene(cmd, id)
		"reload_scene":
			return _cmd_reload_scene(cmd, id)
		"screenshot":
			return _cmd_screenshot(cmd, id)
		"get_logs":
			return _cmd_get_logs(cmd, id)
		"clear_logs":
			return _cmd_clear_logs(cmd, id)
		"set_log_verbosity":
			return _cmd_set_log_verbosity(cmd, id)
		"log_message":
			return _cmd_log_message(cmd, id)
		"perf_get_stats":
			return _cmd_perf_get_stats(cmd, id)
		"perf_enable":
			return _cmd_perf_enable(cmd, id)
		"perf_disable":
			return _cmd_perf_disable(cmd, id)
		"perf_reset":
			return _cmd_perf_reset(cmd, id)
		"locator_find":
			return _cmd_locator_find(cmd, id)
		"locator_action":
			return _cmd_locator_action(cmd, id)
		"quit":
			return _cmd_quit(cmd, id)
		_:
			return {"id": id, "error": "Unknown command: " + action}


# ---------------------------------------------------------------------------
# Node Operations (instant)
# ---------------------------------------------------------------------------

func _cmd_node_exists(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var node = _server.get_tree().root.get_node_or_null(path)
	return {"id": id, "exists": node != null}


func _cmd_get_property(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var property: String = cmd.get("property", "")
	var node = _server.get_tree().root.get_node_or_null(path)
	if node == null:
		return {"id": id, "error": "Node not found: " + path}
	var value = node.get_indexed(property)
	if value == null and not property in _get_property_list_names(node):
		# Check if base property exists (before colon)
		var base_prop: String = property.split(":")[0]
		if node.get(base_prop) == null and not base_prop in _get_property_list_names(node):
			return {"id": id, "error": "Property not found: " + property + " on " + path}
	return {"id": id, "result": JsonSerializer.serialize(value)}


func _cmd_set_property(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var property: String = cmd.get("property", "")
	var raw_value = cmd.get("value")
	var node = _server.get_tree().root.get_node_or_null(path)
	if node == null:
		return {"id": id, "error": "Node not found: " + path}
	var value = JsonSerializer.deserialize(raw_value)
	node.set_indexed(property, value)
	return {"id": id, "ok": true}


func _cmd_call_method(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var method: String = cmd.get("method", "")
	var raw_args: Array = cmd.get("args", [])
	var node = _server.get_tree().root.get_node_or_null(path)
	if node == null:
		return {"id": id, "error": "Node not found: " + path}
	var args: Array = []
	for arg in raw_args:
		args.append(JsonSerializer.deserialize(arg))
	if not node.has_method(method):
		return {"id": id, "error": "Method call failed: " + method + " not found on " + path}
	var result = node.callv(method, args)
	return {"id": id, "result": JsonSerializer.serialize(result)}


func _cmd_find_by_group(cmd: Dictionary, id) -> Dictionary:
	var group: String = cmd.get("group", "")
	var nodes: Array = _server.get_tree().get_nodes_in_group(group)
	var paths: Array = []
	for node in nodes:
		paths.append(str(node.get_path()))
	return {"id": id, "nodes": paths}


func _cmd_query_nodes(cmd: Dictionary, id) -> Dictionary:
	var pattern: String = cmd.get("pattern", "")
	var group: String = cmd.get("group", "")
	var results: Array = []

	if not group.is_empty():
		var group_nodes: Array = _server.get_tree().get_nodes_in_group(group)
		if pattern.is_empty():
			for node in group_nodes:
				results.append(str(node.get_path()))
		else:
			for node in group_nodes:
				if node.name.match(pattern):
					results.append(str(node.get_path()))
	elif not pattern.is_empty():
		_walk_tree_match(_server.get_tree().root, pattern, results)

	return {"id": id, "nodes": results}


func _walk_tree_match(node: Node, pattern: String, results: Array) -> void:
	if node.name.match(pattern):
		results.append(str(node.get_path()))
	for child in node.get_children():
		_walk_tree_match(child, pattern, results)


func _cmd_get_tree(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "/root")
	var max_depth: int = cmd.get("depth", 10)
	var root_node = _server.get_tree().root.get_node_or_null(path)
	if root_node == null:
		return {"id": id, "error": "Node not found: " + path}
	var tree_data: Dictionary = _build_tree_dict(root_node, max_depth, 0)
	return {"id": id, "tree": tree_data}


func _build_tree_dict(node: Node, max_depth: int, current_depth: int) -> Dictionary:
	var result: Dictionary = {
		"name": node.name,
		"type": node.get_class(),
		"path": str(node.get_path()),
		"children": [],
	}
	if current_depth < max_depth:
		for child in node.get_children():
			result["children"].append(_build_tree_dict(child, max_depth, current_depth + 1))
	return result


func _cmd_batch(cmd: Dictionary, id) -> Dictionary:
	var commands: Array = cmd.get("commands", [])
	var results: Array = []
	for sub_cmd in commands:
		var sub_result: Dictionary = execute(sub_cmd)
		if sub_result.has("_deferred"):
			results.append({"id": sub_cmd.get("id", null), "error": "Deferred commands not supported in batch"})
		else:
			results.append(sub_result)
	return {"id": id, "results": results}


# ---------------------------------------------------------------------------
# Locator — multi-strategy node resolution
# ---------------------------------------------------------------------------

func _cmd_locator_find(cmd: Dictionary, id) -> Dictionary:
	var filters: Array = cmd.get("filters", [])
	var multi: String = cmd.get("multi", "error")
	var timeout: float = cmd.get("timeout", 5.0)

	if filters.is_empty():
		return {"id": id, "error": "locator_find requires at least one filter"}

	var nodes: Array = []
	var first_filter: Dictionary = filters[0]
	var strategy: String = first_filter.get("strategy", "path")
	var value: String = first_filter.get("value", "")
	var pattern: String = first_filter.get("pattern", "")

	match strategy:
		"path", "path_pattern":
			if value.begins_with("/"):
				var node = _server.get_tree().root.get_node_or_null(value)
				if node != null:
					nodes = [node]
			else:
				# Wildcard path matching
				_walk_path_match(_server.get_tree().root, value, nodes)
		"name":
			_walk_name_match(_server.get_tree().root, value, nodes)
		"group":
			nodes = _server.get_tree().get_nodes_in_group(value)
		"text":
			_walk_text_match(_server.get_tree().root, value, nodes)
		"type":
			_walk_type_match(_server.get_tree().root, value, nodes)
		"script":
			_walk_script_match(_server.get_tree().root, value, nodes)
		_:
			return {"id": id, "error": "Unknown locator strategy: " + strategy}

	# Apply chained filters (filters[1:]).
	for i in range(1, filters.size()):
		var f: Dictionary = filters[i]
		var f_strategy: String = f.get("strategy", "")
		var f_value: String = f.get("value", "")
		match f_strategy:
			"name":
				nodes = _filter_by_name(nodes, f_value)
			"group":
				nodes = _filter_by_group(nodes, f_value)
			"text":
				nodes = _filter_by_text(nodes, f_value)
			"type":
				nodes = _filter_by_type(nodes, f_value)
			"script":
				nodes = _filter_by_script(nodes, f_value)
			"visible":
				nodes = _filter_visible(nodes)
			_:
				return {"id": id, "error": "Unknown filter strategy: " + f_strategy}

	var paths: Array = []
	for node in nodes:
		paths.append(str(node.get_path()))

	# Multi-match handling
	if paths.size() > 1 and multi == "error":
		return {
			"id": id,
			"error": "locator_ambiguous",
			"message": "Locator matched %d nodes (expected 1). Use .first, .nth(i), or .all." % paths.size(),
			"nodes": paths,
		}
	if multi == "first" and paths.size() > 0:
		paths = [paths[0]]
	elif multi == "nth":
		var index: int = cmd.get("nth", 0)
		if index >= 0 and index < paths.size():
			paths = [paths[index]]
		else:
			paths = []

	return {"id": id, "nodes": paths}


func _cmd_locator_action(cmd: Dictionary, id) -> Dictionary:
	var find_result: Dictionary = _cmd_locator_find(cmd, id)
	if find_result.has("error"):
		return find_result

	var paths: Array = find_result.get("nodes", [])
	if paths.is_empty():
		return {"id": id, "error": "node_not_found", "message": "Locator matched no nodes"}

	var action: String = cmd.get("locator_action", "")
	var target_path: String = paths[0]

	match action:
		"click":
			return _cmd_click_node({"path": target_path}, id)
		"get_property":
			return _cmd_get_property({
				"path": target_path,
				"property": cmd.get("property", ""),
			}, id)
		"set_property":
			return _cmd_set_property({
				"path": target_path,
				"property": cmd.get("property", ""),
				"value": cmd.get("value"),
			}, id)
		"call":
			return _cmd_call_method({
				"path": target_path,
				"method": cmd.get("method", ""),
				"args": cmd.get("args", []),
			}, id)
		"exists":
			return {"id": id, "exists": true}
		"wait_visible":
			var node = _server.get_tree().root.get_node_or_null(target_path)
			if node is Control:
				if node.is_visible_in_tree():
					return {"id": id, "ok": true}
				return {
					"_deferred": true,
					"wait_type": "property",
					"path": target_path,
					"property": "visible",
					"value": true,
					"timeout": cmd.get("timeout", 5.0),
					"id": id,
					"response": {"id": id, "ok": true},
				}
			return {"id": id, "ok": true, "message": "Node is not a Control; visibility check skipped"}
		_:
			return {"id": id, "error": "Unknown locator action: " + action}


# ---------------------------------------------------------------------------
# Locator tree walk helpers
# ---------------------------------------------------------------------------

func _walk_path_match(node: Node, pattern: String, results: Array) -> void:
	if _path_matches(node, pattern):
		results.append(node)
	for child in node.get_children():
		_walk_path_match(child, pattern, results)


func _path_matches(node: Node, pattern: String) -> bool:
	# Simple */name pattern matching
	if pattern.ends_with("/*"):
		return true  # Any node at this level
	var node_path: String = str(node.get_path())
	if pattern.begins_with("*/"):
		return node_path.ends_with(pattern.substr(1))
	return node_path.match(pattern)


func _walk_name_match(node: Node, pattern: String, results: Array) -> void:
	if node.name.match(pattern):
		results.append(node)
	for child in node.get_children():
		_walk_name_match(child, pattern, results)


func _walk_text_match(node: Node, text: String, results: Array) -> void:
	if node is Control:
		if "text" in node and str(node.get("text")) == text:
			results.append(node)
	for child in node.get_children():
		_walk_text_match(child, text, results)


func _walk_type_match(node: Node, type_name: String, results: Array) -> void:
	if node.get_class() == type_name:
		results.append(node)
	for child in node.get_children():
		_walk_type_match(child, type_name, results)


func _walk_script_match(node: Node, script_name: String, results: Array) -> void:
	var scr = node.get_script()
	if scr != null:
		var path: String = scr.resource_path
		if path.ends_with(script_name) or path.match(script_name):
			results.append(node)
	for child in node.get_children():
		_walk_script_match(child, script_name, results)


# ---------------------------------------------------------------------------
# Locator filter helpers (operate on node arrays)
# ---------------------------------------------------------------------------

func _filter_by_name(nodes: Array, pattern: String) -> Array:
	var out: Array = []
	for node in nodes:
		if node.name.match(pattern):
			out.append(node)
	return out


func _filter_by_group(nodes: Array, group: String) -> Array:
	var out: Array = []
	for node in nodes:
		if node.is_in_group(group):
			out.append(node)
	return out


func _filter_by_text(nodes: Array, text: String) -> Array:
	var out: Array = []
	for node in nodes:
		if node is Control and "text" in node and str(node.get("text")) == text:
			out.append(node)
	return out


func _filter_by_type(nodes: Array, type_name: String) -> Array:
	var out: Array = []
	for node in nodes:
		if node.get_class() == type_name:
			out.append(node)
	return out


func _filter_by_script(nodes: Array, script_name: String) -> Array:
	var out: Array = []
	for node in nodes:
		var scr = node.get_script()
		if scr != null:
			var path: String = scr.resource_path
			if path.ends_with(script_name) or path.match(script_name):
				out.append(node)
	return out


func _filter_visible(nodes: Array) -> Array:
	var out: Array = []
	for node in nodes:
		if node is CanvasItem and node.visible:
			out.append(node)
	return out


# ---------------------------------------------------------------------------
# Input Simulation (deferred)
# ---------------------------------------------------------------------------

func _cmd_input_key(cmd: Dictionary, id) -> Dictionary:
	var keycode: int = cmd.get("keycode", 0)
	var pressed: bool = cmd.get("pressed", true)
	var physical: bool = cmd.get("physical", false)

	var event := InputEventKey.new()
	if physical:
		event.physical_keycode = keycode
	else:
		event.keycode = keycode
	event.pressed = pressed

	Input.parse_input_event(event)

	return {
		"_deferred": true,
		"wait_type": "physics_frames",
		"count": 2,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_input_action(cmd: Dictionary, id) -> Dictionary:
	var action_name: String = cmd.get("action_name", "")
	var pressed: bool = cmd.get("pressed", true)
	var strength: float = cmd.get("strength", 1.0)

	var event := InputEventAction.new()
	event.action = action_name
	event.pressed = pressed
	event.strength = strength

	Input.parse_input_event(event)

	return {
		"_deferred": true,
		"wait_type": "physics_frames",
		"count": 2,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_input_mouse_button(cmd: Dictionary, id) -> Dictionary:
	var x: float = cmd.get("x", 0.0)
	var y: float = cmd.get("y", 0.0)
	var button_index: int = cmd.get("button", 1)
	var pressed: bool = cmd.get("pressed", true)

	var event := InputEventMouseButton.new()
	event.position = Vector2(x, y)
	event.global_position = event.position
	event.button_index = button_index
	event.pressed = pressed

	Input.parse_input_event(event)

	return {
		"_deferred": true,
		"wait_type": "physics_frames",
		"count": 2,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_input_mouse_motion(cmd: Dictionary, id) -> Dictionary:
	var x: float = cmd.get("x", 0.0)
	var y: float = cmd.get("y", 0.0)
	var rel_x: float = cmd.get("relative_x", 0.0)
	var rel_y: float = cmd.get("relative_y", 0.0)

	var event := InputEventMouseMotion.new()
	event.position = Vector2(x, y)
	event.global_position = event.position
	event.relative = Vector2(rel_x, rel_y)

	Input.parse_input_event(event)

	return {
		"_deferred": true,
		"wait_type": "physics_frames",
		"count": 2,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_click_node(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var node = _server.get_tree().root.get_node_or_null(path)
	if node == null:
		return {"id": id, "error": "Node not found: " + path}

	var screen_pos := Vector2.ZERO

	if node is Control:
		screen_pos = node.get_global_rect().get_center()
	elif node is Node2D:
		screen_pos = node.get_viewport_transform() * node.get_global_transform() * Vector2.ZERO
	else:
		return {"id": id, "error": "Cannot determine screen position for node: " + path}

	var press_event := InputEventMouseButton.new()
	press_event.position = screen_pos
	press_event.global_position = screen_pos
	press_event.button_index = MOUSE_BUTTON_LEFT
	press_event.pressed = true
	Input.parse_input_event(press_event)

	var release_event := InputEventMouseButton.new()
	release_event.position = screen_pos
	release_event.global_position = screen_pos
	release_event.button_index = MOUSE_BUTTON_LEFT
	release_event.pressed = false
	Input.parse_input_event(release_event)

	return {
		"_deferred": true,
		"wait_type": "physics_frames",
		"count": 2,
		"id": id,
		"response": {"id": id, "ok": true},
	}


# ---------------------------------------------------------------------------
# Frame Sync (deferred)
# ---------------------------------------------------------------------------

func _cmd_wait_process_frames(cmd: Dictionary, id) -> Dictionary:
	var count: int = cmd.get("count", 1)
	return {
		"_deferred": true,
		"wait_type": "process_frames",
		"count": count,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_wait_physics_frames(cmd: Dictionary, id) -> Dictionary:
	var count: int = cmd.get("count", 1)
	return {
		"_deferred": true,
		"wait_type": "physics_frames",
		"count": count,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_wait_seconds(cmd: Dictionary, id) -> Dictionary:
	var duration: float = cmd.get("seconds", 1.0)
	return {
		"_deferred": true,
		"wait_type": "seconds",
		"duration": duration,
		"id": id,
		"response": {"id": id, "ok": true},
	}


# ---------------------------------------------------------------------------
# Synchronization (deferred)
# ---------------------------------------------------------------------------

func _cmd_wait_for_node(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var timeout: float = cmd.get("timeout", 5.0)
	return {
		"_deferred": true,
		"wait_type": "node_exists",
		"path": path,
		"timeout": timeout,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_wait_for_signal(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var signal_name: String = cmd.get("signal_name", "")
	var timeout: float = cmd.get("timeout", 5.0)
	return {
		"_deferred": true,
		"wait_type": "signal",
		"path": path,
		"signal_name": signal_name,
		"timeout": timeout,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_wait_for_property(cmd: Dictionary, id) -> Dictionary:
	var path: String = cmd.get("path", "")
	var property: String = cmd.get("property", "")
	var expected = cmd.get("value")
	var timeout: float = cmd.get("timeout", 5.0)
	return {
		"_deferred": true,
		"wait_type": "property",
		"path": path,
		"property": property,
		"value": expected,
		"timeout": timeout,
		"id": id,
		"response": {"id": id, "ok": true},
	}


# ---------------------------------------------------------------------------
# Scene Management
# ---------------------------------------------------------------------------

func _cmd_get_scene(_cmd: Dictionary, id) -> Dictionary:
	var current_scene = _server.get_tree().current_scene
	if current_scene == null:
		return {"id": id, "error": "No current scene"}
	return {"id": id, "scene": current_scene.scene_file_path}


func _cmd_change_scene(cmd: Dictionary, id) -> Dictionary:
	var scene_path: String = cmd.get("scene_path", "")
	_server.get_tree().change_scene_to_file(scene_path)
	return {
		"_deferred": true,
		"wait_type": "scene_change",
		"scene_path": scene_path,
		"id": id,
		"response": {"id": id, "ok": true},
	}


func _cmd_reload_scene(_cmd: Dictionary, id) -> Dictionary:
	var current_scene = _server.get_tree().current_scene
	if current_scene == null:
		return {"id": id, "error": "No current scene to reload"}
	var scene_path: String = current_scene.scene_file_path
	_server.get_tree().change_scene_to_file(scene_path)
	return {
		"_deferred": true,
		"wait_type": "scene_change",
		"scene_path": scene_path,
		"id": id,
		"response": {"id": id, "ok": true},
	}


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

func _cmd_screenshot(cmd: Dictionary, id) -> Dictionary:
	var image: Image = _server.get_viewport().get_texture().get_image()
	if image == null:
		return {"id": id, "error": "Failed to capture screenshot"}

	var save_path: String = cmd.get("save_path", "")
	if save_path.is_empty():
		var timestamp: String = Time.get_datetime_string_from_system().replace(":", "-")
		save_path = "user://e2e_screenshots/" + timestamp + ".png"
		DirAccess.make_dir_recursive_absolute(save_path.get_base_dir())

	image.save_png(save_path)

	var abs_path: String = save_path
	if save_path.begins_with("user://") or save_path.begins_with("res://"):
		abs_path = ProjectSettings.globalize_path(save_path)

	return {"id": id, "ok": true, "path": abs_path}


# ---------------------------------------------------------------------------
# Log Capture
# ---------------------------------------------------------------------------

func _cmd_get_logs(cmd: Dictionary, id) -> Dictionary:
	var verbosity: String = cmd.get("verbosity", "")
	var logs: Array = _server.get_logs(verbosity)
	return {"id": id, "logs": logs}


func _cmd_clear_logs(_cmd: Dictionary, id) -> Dictionary:
	_server.clear_logs()
	return {"id": id, "ok": true}


func _cmd_set_log_verbosity(cmd: Dictionary, id) -> Dictionary:
	var level: String = cmd.get("level", "error")
	_server.set_log_verbosity(level)
	return {"id": id, "ok": true}


func _cmd_log_message(cmd: Dictionary, id) -> Dictionary:
	var level: String = cmd.get("level", "info")
	var message: String = cmd.get("message", "")
	_server.add_log(level, message)
	return {"id": id, "ok": true}


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------

func _cmd_perf_get_stats(_cmd: Dictionary, id) -> Dictionary:
	var stats: Dictionary = _server.get_perf_stats()
	return {"id": id, "stats": stats}


func _cmd_perf_enable(_cmd: Dictionary, id) -> Dictionary:
	_server.enable_perf_monitoring()
	return {"id": id, "ok": true}


func _cmd_perf_disable(_cmd: Dictionary, id) -> Dictionary:
	_server.disable_perf_monitoring()
	return {"id": id, "ok": true}


func _cmd_perf_reset(_cmd: Dictionary, id) -> Dictionary:
	_server.reset_perf_stats()
	return {"id": id, "ok": true}


# ---------------------------------------------------------------------------
# Quit
# ---------------------------------------------------------------------------

func _cmd_quit(cmd: Dictionary, id) -> Dictionary:
	var exit_code: int = cmd.get("exit_code", 0)
	_server.get_tree().quit(exit_code)
	return {"id": id, "ok": true}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func _get_property_list_names(node: Node) -> Array:
	var names: Array = []
	for prop in node.get_property_list():
		names.append(prop["name"])
	return names
