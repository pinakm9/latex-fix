import os
import re 

folder = '../test/steady-tex'


def find_files(folder, ext):
    files = []
    for file in os.listdir(folder):
        if file.endswith(ext):
            files.append(folder + '/' + file) 
    return files


def search_file(file):
    with open(file) as f:
        data = f.read()
        refs = re.findall(r'ef{[^}]+}', data)
        labels = re.findall(r'label{[^}]+}', data)
    return refs, labels


def fix(file, refs, labels, tag):
    with open(file) as f:
        data = f.read()
        for ref in refs:
            data = data.replace(ref, ref[:-1] + tag + '}')
        for label in labels:
            data = data.replace(label, label[:-1] + tag + '}')
    with open(file, 'w') as f:
        f.write(data)
        

def unfix(file, refs, labels, tag):
    with open(file) as f:
        data = f.read()
        for ref in refs:
            data = data.replace(ref, ref[:-1][:-len(tag)] + '}')
        for label in labels:
            data = data.replace(label, label[:-1][:-len(tag)] + '}')
    with open(file, 'w') as f:
        f.write(data)


def fixall(folder, ext, tag):
    files = find_files(folder, ext)
    for file in files:
        refs, labels = search_file(file)
        fix(file, refs, labels, tag)

def unfixall(folder, ext, tag):
    files = find_files(folder, ext)
    for file in files:
        refs, labels = search_file(file)
        unfix(file, refs, labels, tag)

# file = find_files(folder, 'tex')[-1]
# refs, labels = search_file(file)
# print(refs)
# print(labels)
# unfix(file, refs, labels, '-chapter3')

unfixall(folder, 'tex', '--ch3')