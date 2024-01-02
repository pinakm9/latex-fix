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


        if mode == 'clear_folder':
            # remove all non-zip folders
            for f in os.scandir(root_folder):
                if not f.path.endswith('.zip'):
                    try:
                        shutil.rmtree(f.path)
                    except:
                        pass
        
        # unzip all zip files and remove them
        for f in os.scandir(root_folder):
            if f.path.endswith('.zip'):
                with zipfile.ZipFile(f.path, 'r') as zip_ref:
                    zip_ref.extractall(f.path[:-4])
                self.chapters.append(os.path.basename(f.path)[:-4])
                self.folders.append(f.path[:-4])
                if mode == 'clear_zip':
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
                abstract = re.findall(r'{abstract}[^\\]+', data)[0][10:]
                with open(folder + '/abstract.tex', 'w') as abstract_file:
                    abstract_file.write(abstract)
                title = re.findall(r'\\title{[^}]+}', data)[0]
                title_commands = re.findall(r'\\\S*', title[6:])
                for command in title_commands:
                    title = title.replace(command, '')
                sections = re.findall(r'\\section[^#]+end{document', data)[0]
                biblio =  re.findall(r'\\bibliography[^{]*{[^}]*}', data)
                new_data = title.replace('title', 'chapter') + '\n' + sections[:-13]
                for text in biblio:
                    new_data = new_data.replace(text, '')
                with open(folder + '/main.tex', 'w') as file:
                    file.write('\chapter*{Chapter \getnextid{' + 'chapter}}\n\\textit{\input{'\
                                +f'{self.chapters[i]}' + '/abstract}}\n\\newpage\n\n')
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
                    try:
                        shutil.rmtree(folder + '/' + obj)
                    except:
                        os.remove(folder + '/' + obj)
        
        

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
        imgs =  list(map(str, Path(folder).rglob('*.png'))) + list(map(str, Path(folder).rglob('*.jpg')))
        # print(imgs)
        return imgs 
    
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
          



class Combiner(Fixer):
    def __init__(self, root_folder, tag, mode=None):
        super().__init__(root_folder, mode)
        self.new_folder = self.root + f'/{tag}'
        
        if not os.path.exists(self.new_folder + '/plots'):
            os.makedirs(self.new_folder + '/plots')
        

        for i, folder in enumerate(self.folders):
            # fix paths
            for  file in self.find_tex(folder):
                with open(file, 'r') as f:
                    data = f.read()
                
                paths = re.findall(r'input{[^}]+', data)
                for path in paths:
                    data = data.replace(path, path + '--' + self.chapters[i])
                
                with open(file, 'w') as f:
                    f.write(data.replace(self.chapters[i] + '/', tag + '/'))
                
                name, ext = file[:-4], file[-4:]
                new_file = name + '--' + self.chapters[i] + ext
                shutil.move(file, new_file.replace(self.chapters[i] + '/', tag + '/'))

            for file in self.find_img(folder):
                shutil.move(file, file.replace(self.chapters[i] + '/', tag + '/'))

            shutil.rmtree(folder)
        
        shutil.move(self.root + '/ref-combined.bib', self.new_folder + '/ref-combined.bib')

            

        
    
    # def add_index(self, files, index):
    #     new_files = []
    #     for file in files:
    #         name, ext = file[:-4], file[-4:]
    #         new_files.append(name + '_' + str(index) + ext)
    #     return new_files
    
    # def move_new_files(self, files, new_folder, index):
    #     if not os.path.exists(new_folder):
    #         os.makedirs(new_folder)
    #     for file in files:
    #         shutil.move(file, new_folder + f'/{self.add_index([os.path.basename(file)], index)[0]}')


    # def move_new_imgs(self, folder, new_folder, index):
    #     if not os.path.exists(new_folder + '/plots'):
    #         os.makedirs(new_folder + '/plots')
        
    #     for file in os.listdir(folder + '/plots'):
    #         file = os.path.basename(file)
    #         img_path = folder + '/plots/' + file
    #         new_path = new_folder + '/plots/' + self.add_index([file], index)[0]
    #         # print(img_path, new_path)
    #         shutil.move(img_path, new_path)


    # def fix_paths(self, file, tex_paths, img_paths, tag):
    #     with open(file, 'r') as f:
    #         data = f.read()
    #         for path in tex_paths:
    #             left, right = path.index('{'), path.index('}')
    #             file_ = os.path.basename(path[left+1:right])
    #             data = data.replace(path, path[:left+1] + tag + '/' + file_ + path[right:])
    #         for path in img_paths:
    #             left, right = path.index('{'), path.index('}')
    #             new_path = self.get_new_img_ref(path[left+1:right], tag)
    #             new_path = path[:left+1] + new_path + path[right:]
    #             # print(path, new_path)
    #             data = data.replace(path, new_path)
 