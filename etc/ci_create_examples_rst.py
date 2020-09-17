import os
import re
import shutil
from subprocess import Popen, PIPE

# get list of examples from body.text
ex_regex = re.compile("\\\\input{sections/(.*?)\\}")
ex_list = []
pth = os.path.join("..", "doc", "body.tex")
with open(pth) as f:
    lines = f.read()
for v in ex_regex.findall(lines):
    ex_list.append(v.replace(".tex", ""))

# create examples rst
pth = os.path.join("..", ".doc", "examples.rst")
print("creating...'{}'".format(pth))
f = open(pth, "w")
line = "============================\n"
line += "MODFLOW 6 – Example problems\n"
line += "============================\n\n\n"
line += ".. toctree::\n"
line += "   :maxdepth: 1\n\n"
for ex in ex_list:
    line += "   _examples/{}\n".format(ex)
f.write(line)
f.close()

# create rtd examples directory
dst = os.path.join("..", ".doc", "_examples")
print("cleaning and creating...'{}'".format(dst))
if os.path.isdir(dst):
    shutil.rmtree(dst)
os.makedirs(dst)

# read base latex file
pth = os.path.join("..", "doc", "mf6examples.tex")
print("reading...'{}'".format(pth))
with open(pth) as f:
    orig_latex = f.readlines()

latex_tag = "\\input{./body.tex}"
doc_pth = os.path.join("..", "doc")
for ex in ex_list:
    print("creating restructured text file for {} example".format(ex))
    src = os.path.join("..", "doc", "ex.tex")
    f = open(src, "w")
    for line in orig_latex:
        if latex_tag in line:
            new_tag = "\\input{{sections/{}.tex}}".format(ex)
            line = line.replace(latex_tag, new_tag)
        f.write(line)
    f.close()

    # create restructured text file for example using using pandoc
    dst = os.path.join("..", ".doc", "_examples", "{}.rst".format(ex))
    print("running pandoc to create {}".format(dst))
    args = (
        "pandoc",
        "-s",
        "-f",
        "latex",
        "-t",
        "rst",
        "--bibliography=mf6examples.bib",
        "--csl=wrr.csl",
        "ex.tex",
        "-o",
        dst,
    )
    print(" ".join(args))
    proc = Popen(args, stdout=PIPE, stderr=PIPE, cwd=doc_pth)
    stdout, stderr = proc.communicate()
    if stdout:
        print(stdout.decode("utf-8"))
    if stderr:
        print("Errors:\n{}".format(stderr.decode("utf-8")))

    # read restructured text file for example
    print("reading...'{}'".format(dst))
    with open(dst) as f:
        lines = f.readlines()

    # editing restructured text file for example
    print("editing...'{}'".format(dst))
    f = open(dst, "w")

    write_line = True
    in_reference = False
    for idx, line in enumerate(lines):
        # skip the title
        if idx < 6:
            continue

        tag = ".. figure:: ../figures/"
        if tag in line:
            line = line.replace(tag, ".. figure:: ../_images/")

        tag = ".. figure:: ../images/"
        if tag in line:
            line = line.replace(tag, ".. figure:: ../_images/")

        tag = ":alt:"
        if tag in line:
            write_line = False

        tag = ":name:"
        if not write_line and tag in line:
            write_line = True

        tag = ".. container:: references hanging-indent"
        if tag in line:
            in_reference = True
            line = "References Cited\n----------------\n\n"

        if in_reference:
            tag = ".. container::"
            if tag in line:
                continue

            tag = ":name:"
            if tag in line:
                continue

            if line.startswith("      "):
                line = line.lstrip()

        if write_line:
            f.write(line)

    f.close()

    # clean up temporary latex file
    if os.path.isfile(src):
        os.remove(src)

# create rtd figure directory
dst = os.path.join("..", ".doc", "_images")
print("cleaning and creating...'{}'".format(dst))
if os.path.isdir(dst):
    shutil.rmtree(dst)
os.makedirs(dst)

# copy figures to rtd directory
src_dirs = (os.path.join("..", "figures"),
            os.path.join("..", "images"))
for src_dir in src_dirs:
    file_names = [file_name for file_name in os.listdir(src_dir) if os.path.isfile(
        os.path.join(src_dir, file_name)) and file_name.endswith(".png")]
    for file_name in file_names:
        src = os.path.join(src_dir, file_name)
        print("copy '{}' -> '{}' directory".format(src, dst))
        shutil.copy2(src, dst)