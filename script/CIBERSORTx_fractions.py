import argparse, os, sys
import pandas as pd
import numpy as np

## Parse command-line arguments
parser = argparse.ArgumentParser(description="impute the fractions of previous identified cell subsets under each bulk sample in the LINCS L1000 database.")

parser.add_argument("-i", "--input", required=True, help="path to input directory")
parser.add_argument("-o", "--output", default='./', help="path to output directory, default='./'")
parser.add_argument("-u", "--username", required=True, help="email address registered on CIBERSORTx website")
parser.add_argument("-t", "--token", required=True, help="token obtained from CIBERSORTx website")
parser.add_argument("-r", "--refsample", required=True, default=None, help="absolute path to the single-cell sample file")
parser.add_argument("--celltype", default=None, help="choose a cell line from the options. If no name is provided, we will automatically determine the cell type. Options:  A375 (malignant melanoma),  A549 (non-small cell lung carcinoma),  HCC515 (non-small cell lung adenocarcinoma),  HEPG2 (hepatocellular carcinoma), HT29 (colorectal adenocarcinoma),  MCF7 (breast adenocarcinoma),  PC3 (prostate adenocarcinoma),  YAPC (Pancreatic carcinoma)")

args = parser.parse_args()

function = "docker run --rm --name cibersortx-fractions \
          -v {input_dir}:/src/data -v {output_dir}:/src/outdir \
          cibersortx/fractions --username {username} --token {token} \
          --single_cell TRUE --fraction 0 --rmbatchSmode TRUE ".format(
          input_dir=os.path.abspath(args.input), output_dir=os.path.abspath(args.output), 
          username=args.username, token=args.token)

## Check arguments
cell = ''
if not os.path.exists(args.input):
    sys.exit("The input path does not exist.")
if not os.path.exists(args.output):
    os.makedirs(args.output)
if not args.refsample or not (args.refsample and os.path.isfile(args.refsample)):
    sys.exit("The single-cell sample file does not exist.")
if not args.celltype:
    # automatically determine the cell line
    from scipy.stats import pearsonr
    def find_deg(df):
        deg_list = set()
        for i in range(l:=len(df.columns)):
            Z_i = pd.DataFrame(index=df.index, columns=[0], data=0)
            for j in range(l):
                if (i == j) : continue
                Z_i[0] += (df.iloc[:,i] - df.iloc[:,j])
            Z_i = Z_i[Z_i[0]>0].sort_values(by=0, ascending=False)
            deg_list_i = Z_i.index.tolist()
            deg_list.update(deg_list_i[:min(300, len(deg_list_i))])
        return set(deg_list)

    print("determing the cell line...")
    average_gep = np.log2(pd.read_csv(args.refsample, delimiter='\t', index_col=0, header=0).mean(axis=1)+1)
    cellline_gep = pd.read_csv('/single-cell-analysis/data/bk_2021_gep.csv', sep=',', index_col=0)
    mutual_genes = [x for x in average_gep.index if x in cellline_gep.index]
    mutual_genes = find_deg(cellline_gep.loc[mutual_genes,:])

    max_p = float('-inf')
    for i, c in enumerate(cellline_gep.columns):
        if((p:=pearsonr(average_gep[mutual_genes].to_numpy(), cellline_gep.loc[mutual_genes, c].to_numpy())[0]) > max_p):
            max_p = p
            cell = c
    print("selected cell type = {}".format(cell))
    bulk_path = '/single-cell-analysis/data/LINCS_L1000_GEP_{}.txt'.format(cell)
else:
    if not args.celltype in ['A375','A549','HCC515','HEPG2','HT29','MCF7','PC3','YAPC']:
        sys.exit("Unacceptable cell type.")
    cell = args.celltype
    bulk_path = '/single-cell-analysis/data/LINCS_L1000_GEP_{}.txt'.format(args.celltype)

if not os.path.isfile(bulk_path):
    from cmapPy.pandasGEXpress.parse import parse

    print("The bulk sample file ({}) does not exist. Generating... It may take a few hours.".format(bulk_path))
    
    def downloadFromGEO(filename, url):
        if not os.path.isfile(filename):
            print(filename.rsplit('.',1)[0])
            if 'gctx' in filename and os.path.isfile(filename.rsplit('.',1)[0]):
                return
            print('downloading {} from the GEO website...'.format(filename.rsplit('/',1)[1]))
            from urllib import request
            import shutil
            with request.urlopen(url) as response, open(filename, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            if('gctx' in filename):
                import gzip
                with gzip.open(filename, 'rb') as f_in:
                    with open(filename.rsplit('.',1)[0], 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
    file_inst = '/single-cell-analysis/data/GSE70138_Broad_LINCS_inst_info_2017-03-06.txt.gz'
    file_sig = '/single-cell-analysis/data/GSE70138_Broad_LINCS_gene_info_2017-03-06.txt.gz'
    file_gctx = '/single-cell-analysis/data/GSE70138_Broad_LINCS_Level3_INF_mlr12k_n345976x12328_2017-03-06.gctx.gz'
    downloadFromGEO(file_inst, 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138%5FBroad%5FLINCS%5Finst%5Finfo%5F2017%2D03%2D06%2Etxt%2Egz')
    downloadFromGEO(file_sig, 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138%5FBroad%5FLINCS%5Fgene%5Finfo%5F2017%2D03%2D06%2Etxt%2Egz')
    downloadFromGEO(file_gctx, 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138%5FBroad%5FLINCS%5FLevel3%5FINF%5Fmlr12k%5Fn345976x12328%5F2017%2D03%2D06%2Egctx%2Egz')

    # read inst_info and gene_info
    inst_info = pd.read_csv(file_inst, sep='\t', compression='gzip')
    sig_info = pd.read_csv(file_sig, sep='\t', usecols=['pr_gene_id','pr_gene_symbol'], compression='gzip')

    # select instance ids for a specific cell type
    inst_ids = inst_info['inst_id'][inst_info['cell_id'] == cell]
    # read gctx
    gctoo = parse(file_gctx, cid=inst_ids)
    gctoo.data_df.index = gctoo.data_df.index.astype(int)
    # covert rowids to gene names
    named_df = pd.merge(gctoo.data_df, sig_info, left_index=True, right_on=['pr_gene_id'], validate='1:1')
    max_df = named_df.groupby('pr_gene_symbol').max().dropna().drop(labels='pr_gene_id',axis=1)
    # reverse to non-log for CIBERSORTx
    exp_df = 2**max_df
    exp_df.to_csv(bulk_path, sep='\t')

function += "--refsample {} --mixture {}".format(args.refsample, bulk_path)


## Run CIBERSORTx fractions
os.system(function)