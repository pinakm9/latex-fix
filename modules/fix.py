import os
import re
import zipfile 
import shutil
import utility as ut
import glob
from pathlib import Path
import bibtexparser as bib
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase



class Fixer:
    def __init__(self, root_folder, mode=None):
        self.root = root_folder
        self.chapters = []
        self.folders = []
        self.types = {'plots': ['.png', '.jpg'], 'tex': ['.tex'], }


        if mode == 'clear':
            # remove all non-zip folders
            for f in os.scandir(root_folder):
                if f.is_dir():
                    shutil.rmtree(f.path)
        
        # unzip all zip files and remove them
        for f in os.scandir(root_folder):
            if f.path.endswith('.zip'):
                with zipfile.ZipFile(f.path, 'r') as zip_ref:
                    zip_ref.extractall(f.path[:-4])
                self.chapters.append(os.path.basename(f.path)[:-4])
                self.folders.append(f.path[:-4])
                if mode == 'clear':
                    os.remove(f.path)
        
        # combine bib files
        self.combine_bib(root_folder)
        
        # rearrange tex files and rewrite main
        for i, folder in enumerate(self.folders):
            # rearrange tex files
            self.move_files(self.find_tex(folder), folder)
            # rerrange image files
            self.move_imgs(folder)
            # rewrite main.tex
            if os.path.exists(folder + '/main.tex'):
                with open(folder + '/main.tex', 'r') as file:
                    data = file.read()
                title = re.findall(r'\\title{[^}]+}', data)[0]
                sections = re.findall(r'\\section[^#]+end{document', data)[0]
                biblio =  re.findall(r'\\bibliography[^{]*{[^}]*}', data)
                new_data = title.replace('title', 'chapter') + '\n' + sections[:-13]
                for text in biblio:
                    new_data = new_data.replace(text, '')
                with open(folder + '/main.tex', 'w') as file:
                    file.write(new_data)
       
            


        # fix all references in latex files
        for i, folder in enumerate(self.folders):
            # fix references i.e. \ref \eqref \label
            self.fix_all_refs(folder, ext='.tex', tag='--' + self.chapters[i])
            # fix \include \includegraphics
            self.fix_all_paths(folder, ext='.tex', tag=self.chapters[i])
            # turn paper into chapter
            self.fix_paper(folder)
            # remove files of unnecessary types
            for other_file in self.find_other(folder, ['.cls', '.bst', '.bib']):
                os.remove(other_file)
            # remove everything but tex files and plots folder
            for obj in os.listdir(folder):
                if obj != 'plots' and not obj.endswith('.tex'):
                    shutil.rmtree(folder + '/' + obj)
        
        

        # fix all file-paths in latex files:



    
    
    
    def fix_paper(self, folder):
        for tex_file in self.find_tex(folder):
            with open(tex_file, 'r') as file:
                data = file.read().replace('this paper', 'this chapter')
            with open(tex_file, 'w') as file:
                file.write(data)

    def get_new_img_ref(self, img_path, folder):
        return folder + '/plots/' + img_path.replace('/', '-')
    
    def get_new_img_path(self, img_path):
        i = img_path.index('/')
        j = img_path[i+1:].index('/')
        k = img_path[i+j+2:].index('/')
        return img_path[:i+j+k+3] + 'plots/' + img_path[i+j+k+3:].replace('/', '-')


    def move_imgs(self, folder):
        if not os.path.exists(folder + '/plots'):
            os.makedirs(folder + '/plots')
        
        for img_path in self.find_img(folder):
            new_path = self.get_new_img_path(img_path)
            # print(img_path, new_path)
            shutil.move(img_path, new_path)
        

            
                
    def read_bib(self, folder):
        data = ''
        for bib_file in self.find_bib(folder):
            with open(bib_file, 'r') as file:
                data += '\n' + file.read()
        parser = BibTexParser(common_strings=False)
        parser.ignore_nonstandard_types = False
        parser.homogenise_fields = False 
        bib_database = bib.loads(data, parser)
        return bib_database.entries
    

    
    def prune_bib(self, entries):
        all_ids = sorted(list(set([entry['ID'] for entry in entries])), key=str.casefold)
        # print(all_ids)
        new_entries = []
        for ID in all_ids:
            for entry in entries:
                if entry['ID'] == ID:
                    new_entries.append(entry)
                    break
        return new_entries
    
    @ut.timer
    def combine_bib(self, folder):
        db = BibDatabase()
        db.entries = self.prune_bib(self.read_bib(folder))
        writer = BibTexWriter()
        writer.indent = '    '     # indent entries with 4 spaces instead of one
        # writer.comma_first = True  # place the comma at the beginning of the line
        with open(f'{folder}/ref-combined.bib', 'w') as bibfile:
            bibfile.write(writer.write(db))
        print(f'Number of unique entries written = {len(db.entries)}')

    
    
                
    

    def find_tex(self, folder):
        return list(map(str, Path(folder).rglob('*.tex')))
    
    def find_bib(self, folder):
        return list(map(str, Path(folder).rglob('*.bib')))
    
    def find_img(self, folder):
        return list(map(str, Path(folder).rglob('*.png'))) + list(map(str, Path(folder).rglob('*.jpg'))) 
    
    def find_other(self, folder, exts):
        files = []
        for ext in exts:
            files += list(map(str, Path(folder).rglob('*' + ext)))
        return  files
    
    def move_files(self, files, new_folder):
        if not os.path.exists(new_folder):
            os.makedirs(new_folder)
        for file in files:
            shutil.move(file, new_folder + f'/{os.path.basename(file)}')

    def remove_empty(self, folder):
        folders = list(os.walk(folder))[1:]
        for folder in folders:
            if not folder[2]:
                os.rmdir(folder[0])

    def find_files(self, folder, ext):
        files = []
        for file in os.listdir(folder):
            if file.endswith(ext):
                files.append(folder + '/' + file) 
        return files

    def search_refs(self, file):
        with open(file) as f:
            data = f.read()
            refs = re.findall(r'ref{[^}]+}', data)
            labels = re.findall(r'label{[^}]+}', data)
        return refs, labels
    
    def search_paths(self, file):
        with open(file) as f:
            data = f.read()
            tex_paths = re.findall(r'input{[^}]+}', data)
            img_paths = re.findall(r'includegraphics[^{]*{[^}]+}', data)
        return tex_paths, img_paths
    
    def fix_refs(self, file, refs, labels, tag):
        with open(file, 'r') as f:
            data = f.read()
            for ref in refs:
                data = data.replace(ref, ref[:-1] + tag + '}')
            for label in labels:
                data = data.replace(label, label[:-1] + tag + '}')
        with open(file, 'w') as f:
            f.write(data)

    def fix_paths(self, file, tex_paths, img_paths, tag):
        with open(file, 'r') as f:
            data = f.read()
            for path in tex_paths:
                left, right = path.index('{'), path.index('}')
                file_ = os.path.basename(path[left+1:right])
                data = data.replace(path, path[:left+1] + tag + '/' + file_ + path[right:])
            for path in img_paths:
                left, right = path.index('{'), path.index('}')
                new_path = self.get_new_img_ref(path[left+1:right], tag)
                new_path = path[:left+1] + new_path + path[right:]
                # print(path, new_path)
                data = data.replace(path, new_path)
     
        with open(file, 'w') as f:    
            f.write(data)

    @ut.timer
    def fix_all_refs(self, folder, ext, tag):
        files = self.find_files(folder, ext)
        for file in files:
            refs, labels = self.search_refs(file)
            self.fix_refs(file, refs, labels, tag)

    @ut.timer
    def fix_all_paths(self, folder, ext, tag):
        files = self.find_files(folder, ext)
        for file in files:
            tex_paths, img_paths = self.search_paths(file)
            self.fix_paths(file, tex_paths, img_paths, tag)
          


    

    




















# folder = '../test/steady-tex'









        

# def unfix(file, refs, labels, tag):
#     with open(file) as f:
#         data = f.read()
#         for ref in refs:
#             data = data.replace(ref, ref[:-1][:-len(tag)] + '}')
#         for label in labels:
#             data = data.replace(label, label[:-1][:-len(tag)] + '}')
#     with open(file, 'w') as f:
#         f.write(data)


# def fixall(folder, ext, tag):
#     files = find_files(folder, ext)
#     for file in files:
#         refs, labels = search_file(file)
#         fix(file, refs, labels, tag)

# def unfixall(folder, ext, tag):
#     files = find_files(folder, ext)
#     for file in files:
#         refs, labels = search_file(file)
#         unfix(file, refs, labels, tag)

# # file = find_files(folder, 'tex')[-1]
# # refs, labels = search_file(file)
# # print(refs)
# # print(labels)
# # unfix(file, refs, labels, '-chapter3')

# unfixall(folder, 'tex', '--ch3')