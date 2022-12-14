# SRA-Importer

An easy and convenient way to import data from the sra database and creating OTU and Taxonomy tables.

## Requirements

The package's use requires:
 - **qiime2 conda environment**: The package must run from qiime2 conda environment. 
If one do not have a qiime2 conda environment installed, follow the instructions from [here](https://docs.qiime2.org/2022.8/install/native/) to install it.   
 - **SRA Toolkit**: The package also depends on SRA Toolkit. 
If one do not have a SRA Toolkit installed, follow the instructions from [here](https://github.com/ncbi/sra-tools/wiki/02.-Installing-SRA-Toolkit) to install it.
Importing is divided to 2 stages:

## Create Visualization

The first stage is in charge of taking the data from the sra database and make a visualization of the reads.
The visualization purpose is to make better assessment of the range in which one should trim and truncate the reads generated by qiime2.

### Parameters
 - `acc_list`: Accession list file. This file must be stored locally.
 - `output_vis_path`: An output path for the visualisation. (Optional)

### Return
The name of the directory created for all the files.

### Usage
```python
from SRA_Importer import visualization

output_dir = visualization(acc_list="AccList.txt", output_vis_path="vis.qzv")
print(output_dir) # .../SRA-Importer-[creation_time]
```

Note: This stage creates a directory. **DO NOT DELETE IT!** Its name is an input to the next stage.

#### In order to decide the trim and trunc values for the next stage, drag and drop the visualization output (.qzv) to [QIIME2-VIEW](https://view.qiime2.org/)

## Export Data

The second stage is in charge of creating OTU and Taxonomy tables and export them into a usable file formats.

### Parameters
 - `output_dir`: The path of the directory created by the first stage.
 - `otu_output_file`: An output path for the OTU table. The directory must exist, and the file's format must be `txt`/`tsv`.
 - `taxonomy_output_file`: An output path for the taxonomy table. The directory must exist, and the file's format must be `tsv`.
 - `classifier_file`: A path to the classifier file. If one needs to download it, it is recommended to download from 
[https://data.qiime2.org/< qiime2-version >/common/gg-13-8-99-nb-classifier.qza](https://data.qiime2.org/2022.8/common/gg-13-8-99-nb-classifier.qza)
#### DADA2 parameters
 - `trim`: a non-negative integer of the right edge of the trimming range. 
If the reads are both forward and reverse a tuple of 2 values is expected.
 - `trunc`: a non-negative integer of the left edge of the truncating range. 
If the reads are both forward and reverse a tuple of 2 values is expected.
 - `threads`: Number of threads to run on. Default is `12`. (Optional)

Note: All the parameters except `threads` must be given.

### Usage
```python
from SRA_Importer import export

export(output_dir="SRA-Importer...", trim=20, trunc=200, 
       classifier_file="gg-13-8-99-nb-classifier.qza", 
       otu_output_file="otu.txt", taxonomy_output_file="taxonomy.tsv")
```