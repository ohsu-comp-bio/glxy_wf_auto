import logging


def get_path(gi, path):
    """
    get_path provides convenient access to Galaxy datasets via a filepath-style
    string, such as "my_library/folder1/folder2/dataset_filename".

    Normally, accessing files via bioblend requires first getting the Galaxy library,
    then getting the folder, then getting the dataset. This helper wraps those steps
    in a more familiar style, based around filepaths.

    For example, given the following tree in Galaxy:
        - Dataset 1
            - Folder A
            - Folder B
                - Folder C
                    - File 1

    "File 1" can be retrieved using:
        gi = bioblend.galaxy.GalaxyInstance(url=galaxy_url, key=galaxy_api_key)
        f = get_path(gi, "Dataset 1/Folder B/Folder C/File 1")

    "Folder C" can be retrieved via "get_path(gi, 'Dataset 1/Folder B/Folder C')"
    "Dataset 1" can be retrieved via "get_path(gi, 'Dataset 1')"

    get_path will raise an exception if it cannot determine the library name,
    or finds more than one library.

    get_path will return None if it can't find a dataset at the path.
    """

    sp = path.split("/")
    if len(sp) == 0:
        raise Exception("cannot determine library")

    library_name = sp[0]
    lib = gi.libraries.get_libraries(name=library_name)
    if not lib:
        return None

    if len(lib) > 1:
        raise Exception('found more than one library named "%s"', library_name)

    lib = lib[0]

    if len(sp) == 1:
        return lib

    subpath = "/" + '/'.join(sp[1:])
    contents = gi.libraries.show_library(lib["id"], contents=True)
    for entry in contents:
        if entry["name"] == subpath:
            return entry

    return None

def make_path(libapi, path):
    """
    make_path is like `mkdir -p` and python's os.makedirs, but for Galaxy.

    make_path will create the library and folders in the given path, e.g.:

        gi = bioblend.galaxy.GalaxyInstance(url=galaxy_url, key=galaxy_api_key)
        make_path(gi.libraries, "foo/bar/baz")

    ...will create the library "foo" and the subfolders "/bar" and "/bar/baz".

    make_path does not return a value.
    """
    sp = path.split("/")
    if len(sp) == 0:
        raise Exception("cannot determine library")

    library_name = sp[0]
    lib = libapi.get_libraries(name=library_name)

    if len(lib) > 1:
        raise Exception('found more than one library named "%s"' % library_name)

    if not lib:
        logging.info("creating library: %s", library_name)
        lib = libapi.create_library(library_name)
    else:
        lib = lib[0]

    if lib["deleted"]:
        raise Exception('''library exists but is deleted: "%s"''' % library_name)

    if len(sp) == 1:
        return

    subpath_parts = sp[1:]
    for i in range(len(subpath_parts)):
        parent = subpath_parts[:i]
        name = subpath_parts[i]
        full = "/" + '/'.join(subpath_parts[:i+1])

        res = libapi.get_folders(lib["id"], name=full)
        if not res:
            kwargs = {
                "library_id": lib["id"],
                "folder_name": name,
            }
            if parent:
                parent_name = "/" + "/".join(parent)
                p = libapi.get_folders(lib["id"], name=parent_name)
                if len(p) > 1:
                    raise Exception(
                        "multiple parent folders for name: {}".format(parent_name))
                if len(p) == 0:
                    raise Exception(
                        "couldn't find parent folder named: {}".format(parent_name))
                kwargs["base_folder_id"] = p[0]["id"]

            logging.info("creating folder: %s", library_name + full)
            libapi.create_folder(**kwargs)[0]
