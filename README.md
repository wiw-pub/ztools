# ztools

PythonSCAD higher level abstraction tools

This is still a work-in-progress. 

# How to load these libraries into your PythonScad scripts?

Two ways:
1. nimport() from web, which is more portable and automated. But limited to the form of `from openscad import *`, and can be victim to function name collisions from multiple libraries.
1. Manually copy libraries over, allowing import aliasing such as `import openscad as oscad`. But less portable as user need to know where to copy libraries from.

## nimport

Libs in public repo supports using nimport(). See https://www.reddit.com/r/OpenPythonSCAD/comments/1g3s2j5/have_your_libraries_with_you_wherever_you_are/m85l097/ for more info.

(Following example is for Windows installation. You can modify the library path based on File > Show Library Folder path).

Copy and paste this into your PythonSCAD script up top.

```py
def load_openscad_thirdparty_lib():
    '''
    Ensure PythonScad loads third party libraries from its pre-designated library folder path.
    '''

    # This is the same path as File > Show Library Folder path.
    LIB_PATH = rf'C:\Users\{os.getlogin()}\Documents\OpenSCAD\libraries'

    if LIB_PATH not in sys.path:
        sys.path.append(LIB_PATH)

# Now call the function
load_openscad_thirdparty_lib()
```

You can optionally verify $PATH has correctly appended in the output window:

```py
print(sys.path)
```

After that, you can use nimport() like this:

```py
nimport('https://raw.githubusercontent.com/willywong/ztools/refs/heads/main/src/honeycomb.py')
nimport('https://raw.githubusercontent.com/willywong/ztools/refs/heads/main/src/ztools.py')
```

This will store a local copy of these libraries from github to your local "File > Show Library Folder" folder.

NOTE: this "replaces" the classic `from honeycomb import *` statement if these libraries were part of stdlib or sourced from pip3. As such, you can't "rename" the imports with this convention.

If you need the flexibility in renaming import aliases, remove the `nimport()` and manually copy those libraries to the designated lib folder, and use standard python import statements such as `import honeycomb as hc`, etc.

## Manually copy libraries over and use standard import aliases.

(To be expanded)

It is recommended to use the same folder as File > Show Library Folder in PythonSCAD for simplicity.

Currently, PythonSCAD does not automatically add this folder to sys.path when loading PythonScad. Be sure to reuse the `load_openscad_thirdparty_lib()` function in the previous section.

Manually copy your libraries to the File > Show Library Folder path.

Execute `load_openscad_thirdparty_lib()` in your PythonSCAD script to setup sys.path

Execute the standard imports such as `import honeycomb as hc`.

# References

PythonSCAD living wiki on various built-in functions https://www.reddit.com/r/OpenPythonSCAD/wiki/index
