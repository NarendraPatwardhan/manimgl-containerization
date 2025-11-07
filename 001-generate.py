import os
import ast
import json
from collections import deque

# --- ============================== ---
# ---         CONFIGURATION          ---
# --- ============================== ---

REPO_BASE_NAME = "3b1b"
OUTPUT_DATASET_DIR = "dataset-v001"
MANIMGL_BASE_SCENES = {"Scene", "InteractiveScene", "ThreeDScene"}
UTILITY_FOLDERS = [os.path.join(REPO_BASE_NAME, "custom"), os.path.join(REPO_BASE_NAME, "once_useful_constructs")]
CONTENT_FOLDERS = [os.path.join(REPO_BASE_NAME, f"_{year}") for year in range(2015, 2026)] + [os.path.join(REPO_BASE_NAME, "outside_videos")]

# --- ============================== ---
# ---      CORE SCRIPT LOGIC         ---
# --- ============================== ---

def get_source_segment(source_code, node):
    return ast.get_source_segment(node=node, source=source_code)

def index_repository(root_path):
    print("Phase 1: Indexing all classes and functions in the repository...")
    class_map, file_map = {}, {}
    all_folders_to_scan = UTILITY_FOLDERS + CONTENT_FOLDERS
    for folder_path in all_folders_to_scan:
        if not os.path.isdir(folder_path): continue
        for subdir, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(subdir, file)
                    relative_path = os.path.relpath(file_path, start=root_path)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            source_code = f.read()
                        tree = ast.parse(source_code)
                        file_info = {"imports": [], "definitions": {}, "source": source_code}
                        for node in tree.body:
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                file_info["imports"].append(get_source_segment(source_code, node))
                            elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                                name = node.name
                                bases = [b.id for b in node.bases if isinstance(b, ast.Name)] if isinstance(node, ast.ClassDef) else []
                                class_map[name] = {"path": relative_path, "source": get_source_segment(source_code, node), "bases": bases, "type": "class" if isinstance(node, ast.ClassDef) else "function"}
                                file_info["definitions"][name] = get_source_segment(source_code, node)
                        file_map[relative_path] = file_info
                    except Exception as e:
                        print(f"  - Warning: Could not parse {file_path}: {e}")
    print(f"Indexing complete. Found {len(class_map)} total definitions.")
    return class_map, file_map

def trace_hierarchy(class_name, class_map):
    hierarchy, visited = [], set()
    current_class = class_name
    while current_class and current_class not in visited:
        hierarchy.append(current_class)
        visited.add(current_class)
        bases = class_map.get(current_class, {}).get("bases", [])
        current_class = bases[0] if bases else None
    return list(reversed(hierarchy))

def identify_special_base_classes(class_map, utility_dirs):
    print("\nPhase 2: Identifying special base classes from utility folders...")
    special_bases = set()
    utility_dirs_abs = [os.path.abspath(d) for d in utility_dirs]
    for name, info in class_map.items():
        if info['type'] != 'class': continue
        full_info_path = os.path.abspath(os.path.join(REPO_BASE_NAME, info['path']))
        if not any(full_info_path.startswith(d) for d in utility_dirs_abs): continue
        if any(base in MANIMGL_BASE_SCENES for base in trace_hierarchy(name, class_map)):
            print(f"  - Found custom base class: {name}")
            special_bases.add(name)
    print(f"Identified {len(special_bases)} special base classes.")
    return special_bases

def analyze_content_folders(class_map, content_dirs):
    print("\nPhase 3: Analyzing scenes in main content folders...")
    analysis_data = {}
    content_dirs_abs = [os.path.abspath(d) for d in content_dirs]
    for name, info in class_map.items():
        if info['type'] != 'class': continue
        full_info_path = os.path.abspath(os.path.join(REPO_BASE_NAME, info['path']))
        if any(full_info_path.startswith(d) for d in content_dirs_abs):
            hierarchy = trace_hierarchy(name, class_map)
            relative_path = info['path']
            if relative_path not in analysis_data: analysis_data[relative_path] = {}
            analysis_data[relative_path][name] = hierarchy
    print(f"Analysis complete. Found scene definitions across {len(analysis_data)} files.")
    return analysis_data

class DependencyFinder(ast.NodeVisitor):
    def __init__(self, local_definitions):
        self.local_definitions = set(local_definitions)
        self.dependencies = set()
    def visit_Name(self, node):
        if node.id in self.local_definitions: self.dependencies.add(node.id)
        self.generic_visit(node)

def has_construct_method(hierarchy, class_map, all_base_classes):
    for class_name in reversed(hierarchy):
        if class_name in all_base_classes: return False
        if class_name in class_map and class_map[class_name]['type'] == 'class':
            try:
                class_def_node = ast.parse(class_map[class_name]['source']).body[0]
                if any(isinstance(n, ast.FunctionDef) and n.name == "construct" for n in class_def_node.body):
                    return True
            except Exception: continue
    return False

def create_dataset(analysis_data, class_map, file_map, special_base_classes):
    print(f"\nPhase 4: Generating dataset in '{OUTPUT_DATASET_DIR}'...")
    if not os.path.exists(OUTPUT_DATASET_DIR): os.makedirs(OUTPUT_DATASET_DIR)
    
    ALL_BASE_CLASSES = MANIMGL_BASE_SCENES.union(special_base_classes)
    scene_counter, total_scenes, skipped_scenes = 0, 0, 0

    for file_path, classes in analysis_data.items():
        for class_name, hierarchy in classes.items():
            if not any(base in ALL_BASE_CLASSES for base in hierarchy): continue
            
            total_scenes += 1
            if not has_construct_method(hierarchy, class_map, ALL_BASE_CLASSES):
                skipped_scenes += 1
                continue

            scene_counter += 1
            print(f"  - ({scene_counter:04d}) Assembling: {class_name}")

            components, imports = {}, set()
            queue = deque([class_name])
            visited = set()
            while queue:
                current_name = queue.popleft()
                if current_name in visited or current_name in MANIMGL_BASE_SCENES: continue
                visited.add(current_name)
                if current_name not in class_map: continue

                info = class_map[current_name]
                components[current_name] = info["source"]
                source_file_info = file_map.get(info["path"])
                if source_file_info:
                    imports.update(source_file_info["imports"])
                    for base in info["bases"]:
                        if base not in visited: queue.append(base)
                    try:
                        finder = DependencyFinder(source_file_info["definitions"].keys())
                        finder.visit(ast.parse(info["source"]))
                        for dep in finder.dependencies:
                            if dep not in visited: queue.append(dep)
                    except Exception: pass

            # --- CRITICAL FIX: Filter out imports that are now irrelevant ---
            included_names = set(components.keys())
            final_imports = []
            for imp_line in imports:
                try:
                    imp_node = ast.parse(imp_line).body[0]
                    if isinstance(imp_node, ast.Import):
                        names = {alias.name for alias in imp_node.names}
                    elif isinstance(imp_node, ast.ImportFrom):
                        names = {alias.name for alias in imp_node.names}
                    
                    if not names.intersection(included_names):
                        final_imports.append(imp_line)
                except (SyntaxError, IndexError):
                    final_imports.append(imp_line) # Keep if parsing fails

            # Replace manim_imports_ext with manimlib
            try:
                index = final_imports.index("from manim_imports_ext import *")
                final_imports[index] = "from manimlib import *"
            except ValueError: pass

            # Assemble the final, ordered file
            main_chain_set = set(hierarchy)
            helpers = {name: src for name, src in components.items() if name not in main_chain_set}
            code_body_parts = [helpers[name] for name in sorted(helpers.keys())]
            code_body_parts += [components[name] for name in hierarchy if name in components]
            
            final_code = f"# Auto-generated from 3b1b/videos repository.\n# Scene: {class_name}\n# Original file: {file_path}\n\n"
            final_code += "\n".join(sorted(list(set(final_imports)))) + "\n\n\n"
            final_code += "\n\n\n".join(code_body_parts)

            with open(os.path.join(OUTPUT_DATASET_DIR, f"{scene_counter:04d}.py"), "w", encoding="utf-8") as f:
                f.write(final_code)

    print("\n--- Generation Summary ---")
    print(f"Total potential scenes found: {total_scenes}")
    print(f"Scenes filtered out (no 'construct' method): {skipped_scenes}")
    print(f"Final dataset size: {scene_counter} files generated in '{OUTPUT_DATASET_DIR}'.")

def main():
    if not os.path.isdir(REPO_BASE_NAME):
        print(f"Error: Repository directory not found: '{REPO_BASE_NAME}'")
        return

    class_map, file_map = index_repository(REPO_BASE_NAME)
    special_base_classes = identify_special_base_classes(class_map, UTILITY_FOLDERS)
    analysis_data = analyze_content_folders(class_map, CONTENT_FOLDERS)
    create_dataset(analysis_data, class_map, file_map, special_base_classes)

if __name__ == "__main__":
    main()
