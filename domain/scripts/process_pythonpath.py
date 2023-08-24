#!/usr/bin/env python3
"""
domain/scripts/fix_pythonpath.py

This file defines FixPythonPath class.

Copyright (C) 2023-today rydnr's pythoneda-shared-pythoneda/artifact

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import argparse
import os
from pathlib import Path
import sys
from typing import List

class FixPythonPath():
    """
    A script to rewrite PYTHONPATH to use local repositories.

    Class name: FixPythonPath

    Responsibilities:
        - Analyze sys.path entries.
        - For each entry, check if they are also available in local folder (relative to the current folder)
        - Print the transformed PYTHONPATH to the standard output.

    Collaborators:
        - None
    """

    def __init__(self):
        """
        Initializes the instance.
        """
        super().__init__()

    def find_modules_under(self, rootFolder:str) -> List[str]:
        """
        Retrieves the names of the Python modules under given folder.
        :param rootFolder: The root folder.
        :type rootFolder: str
        :return: The list of Python modules.
        :rtype: List[str]
        """
        result = []

        exclude_dirs = {'.git', '__pycache__'}
        for dirpath, dirnames, filenames in os.walk(rootFolder):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs ]
            if '__init__.py' in filenames:
                module = os.path.relpath(dirpath, start=rootFolder)
                if module not in result:
                    result.append(module.replace("/", "."))

        return result

    def find_modules_under_pythoneda(self, rootFolder:str) -> List[str]:
        """
        Retrieves the names of the Python modules under given folder.
        :param rootFolder: The root folder.
        :type rootFolder: str
        :return: The list of Python modules.
        :rtype: List[str]
        """
        result = []

        exclude_dirs = {'.git', '__pycache__'}
        for dirpath, dirnames, filenames in os.walk(rootFolder):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs ]
            if '__init__.py' in filenames:
                aux = os.path.relpath(dirpath, start=rootFolder)
                parts = aux.split("/", 2)
                if len(parts) > 2:
                    module = parts[2].replace("/", ".")
                    if module not in result:
                        result.append(module)

        return result

    def find_path_of_pythoneda_package_with_modules(self, rootFolder:str, modules:List[str]) -> str:
        """
        Retrieves the path of the package with given modules.
        :param rootFolder: The root folder.
        :type rootFolder: str
        :param modules: The list of modules.
        :type modules: List[str]
        :return: The path.
        :rtype: str
        """
        module_set = set(modules)
        exclude_dirs = {'.git', '__pycache__'}
        _, orgs, _ = next(os.walk(rootFolder))
        orgs[:] = [d for d in orgs if d not in exclude_dirs ]
        for org in orgs:
            org_folder, repos, _ = next(os.walk(Path(rootFolder) / org))
            repos[:] = [d for d in repos if d not in exclude_dirs ]
            for repo in repos:
                current_modules = self.find_modules_under(Path(org_folder) / repo)
                if set(current_modules) == module_set:
                    return Path(org_folder) / repo

        # If no directory contains all modules, return None
        return None

    def syspath_for_nix_develop(self, sysPath:List, rootFolder: str) -> List:
        """
        Fixes the sys.path collection replacing any PythonEDA entries with their development folders.
        :param sysPath: The sys.path list.
        :type sysPath: List
        :param rootFolder: The root folder.
        :type rootFolder: str
        :return: An alternate sys.path.
        :rtype: List
        """
        result = []
        custom_modules = set(self.find_modules_under_pythoneda(rootFolder))
        for path in sysPath:
            modules_under_path = self.find_modules_under(path)
            if len(modules_under_path) > 0 and modules_under_path[0] == 'pythoneda':
                if all(item in custom_modules for item in modules_under_path):
                    package_path = self.find_path_of_pythoneda_package_with_modules(rootFolder, modules_under_path)
                    if package_path:
                        result.append(str(package_path))
                    else:
                        result.append(path)
                        sys.stderr.write(f'Warning: Could not find alternate path for {path}\n')
                else:
                    sys.stderr.write(f'Warning: submodules mismatch for {path}\n')
#                    for item in modules_under_path:
#                        if item not in custom_modules:
#                            print(f'{item} not present in {custom_modules}')
            else:
                result.append(path)

        return result

    def sort_syspath(self, sysPath:List) -> List:
        """
        Sorts the sys.path entries according to the depth of their .root files.
        :param sysPath: The sys.path list.
        :type sysPath: List
        :return: The new syspath.
        :rtype: List
        """
        unaffected = []
        affected = []
        weights = {}
        for path in sysPath:
            depth = self.find_root_depth(path)
            if depth is None:
                unaffected.append(path)
            else:
                weights[path] = depth
                affected.append(path)

        result = sorted(affected, key=lambda x: weights[x])
        result.extend(unaffected)
        return result

    def find_root_depth(self, path:str) -> int:
        """
        Retrieves the depth of the root, if it exists.
        For example,
        - pythoneda/.pythoneda-root -> 1
        - pythoneda/shared/.pythoneda-root -> 2
        - pythoneda/shared/artifact/.pythoneda-root -> 3
        :param path: The path to check.
        :type path: str
        :return: The depth, or None if no root file is found.
        :rtype: int|None
        """
        result = None
        root_file = self.find_file(".pythoneda-root", path)
        if root_file:
            result = self.count_subfolders(self.relative_path(path, Path(root_file).parent))

        return result

    def find_file(self, targetFile:str, startDir:str='.') -> str:
        """
        Finds a given file within a folder tree.
        :param targetFile: The file to look for.
        :type targetFile: str
        :param startDir: The root folder.
        :type startDir: str
        :return: The path of the file, if found; None otherwise.
        :rtype: str
        """
        start_path = Path(startDir)
        for filepath in start_path.rglob('*'):
            if filepath.name == targetFile:
                return filepath
        return None

    def relative_path(self, base:str, target:str) -> str:
        """
        Retrieves the relative path among two folders.
        :param base: The base folder.
        :type base: str
        :param target: The target folder.
        :type target: str
        :return: The relative path of `target` with respect to `base`; or None if `target` is not relative to `base`.
        :rtype: str|None
        """
        base_path = Path(base).resolve()
        target_path = Path(target).resolve()

        try:
            return str(target_path.relative_to(base_path))
        except ValueError:
            return None

    def count_subfolders(self, path:str) -> int:
        """
        Retrieves the number of subfolders of given path.
        :param path: The path to analyze.
        :type path: str
        :return: The subfolders count.
        :rtype: int
        """
        return len(Path(path).parts)

    def print_syspath(self, sysPath:List):
        """
        Prints the syspath so it can be used to define the PYTHONPATH variable.
        :param sysPath: The sys.path list.
        :type sysPath: List
        """
        print(":".join(sysPath))

    @classmethod
    def main(cls):
        """
        Runs the application from the command line.
        :param file: The file where this specific instance is defined.
        :type file: str
        """
        parser = argparse.ArgumentParser(description="Processes PYTHONPATH")
        parser.add_argument(
            "command",
            choices=["sort", "development" ],
            nargs="?",
            default=None,
            help="The PYTHONPATH processing choices",
        )
        parser.add_argument(
            "-r", "--root-folder", required=False, help="The root folder"
        )
        args, unknown_args = parser.parse_known_args()

        instance = cls()
        root_folder = args.root_folder

        if root_folder is None:
            current_folder = Path(os.getcwd()).resolve()
            root_folder = current_folder.parent.parent

        sys.path = instance.sort_syspath(sys.path)

        if args.command == "development":
            sys.path = instance.syspath_for_nix_develop(sys.path, root_folder)

        instance.print_syspath(sys.path)

if __name__ == "__main__":

    FixPythonPath.main()