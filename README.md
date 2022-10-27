# SRA-Importer

An easy and convenient way to import data from the sra database and creating OTU and Taxonomy tables.

Importing is divided to 2 stages:

## Create Visualization

The first stage is in charge of taking the data from the sra database and make a visualization of the reads.
The visualization purpose is to make better assessment of the range in which one should trim and truncate the reads generated by qiime2.

### Parameters
 - `--sra-study`: SRA experiment code.
 - `--acc-list`: Accession list file. This file must be stored locally.
 - `--output-vis-path`: An output path for the visualisation. (Optional)

Note: Only one of the following must be given `--sra-study`/`--acc-list`. If both are given, an error will be raised.<br>
Usage: 
```
create_vis.py --sra-study <sra-study-code> --acc-list <accession-list-file-path> --output-vis-path <final-output-path-of-visualisation>
```

## Export Data

The second stage is in charge of creating OTU and Taxonomy tables and export them into a usable file formats.

### Parameters
 - `--output-dir`: The path of the directory created by the first stage.
 - `--otu-output-file`: An output path for the OTU table. The directory must exist, and the file's format must be `txt`/`tsv`.
 - `--taxonomy-output-file`: An output path for the taxonomy table. The directory must exist, and the file's format must be `tsv`.
#### DADA2 parameters
 - `--trim`: a non-negative integer of the right edge of the trimming range. 
If the reads are both forward and reverse 2 values should be given seperated with comma: `20,28`
 - `--trunc`: a non-negative integer of the left edge of the truncating range. 
If the reads are both forward and reverse 2 values should be given seperated with comma: `200,220`
 - `--threads`: Number of threads to run on. Default is `12`. (Optional)

Note: All the parameters except `--threads` must be given.<br>
Usage: 
```
export.py --output-dir <output-directory-path> --trim <trim-from> --trunc <trunc-to> --threads <number-of-threads-to-use> --otu-output-file <otu-output-file-path> --taxonomy-output-file <taxonomy-output-file-path>
```

## Recommended Usage

First import 