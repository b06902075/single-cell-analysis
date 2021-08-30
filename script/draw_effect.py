import argparse, os, sys
import pickle
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from treatment_selection import Drug

#plt.style.use('classic')
#
global threshold, con_threshold, pp

def draw_heatmap(df, drugs):
    if len(drugs[0].split('_')) > 1 :
        selected_index = drugs
    else:
        selected_index = [x for x in df.index if x.split('_',1)[0] in drugs]
    if len(selected_index) < 1:
        print('Selected drugs were not used in the treatment selection:')
        print(*drugs)
    else:
        subdf = df.loc[selected_index,:]
        for i in subdf.index:
            for j in subdf.columns:
                if(subdf.loc[i,j] > 0): subdf.loc[i,j] = 0
        sns.set(rc={'figure.figsize':(12,3)})
        ax = sns.heatmap(subdf, center=0, cmap='RdBu', vmin=-1, vmax=0, linewidths=0.5, linecolor='lightgrey', cbar=True)
        for _, spine in ax.spines.items():
            spine.set_visible(True)
            spine.set_color('lightgrey')
        plt.savefig('selected_drug_heatmap.png',bbox_inches='tight')
        print('Heatmap : selected_drug_heatmap.png')



def draw_consistency_plot(index_list, df_effect, df_all):
    index_list = [x for x in index_list if x in df_effect.index]
    index_list = index_list[::-1]
    df = df_effect.loc[index_list,:]
    df_all = df_all.append(df)
    df = df.T
    df.plot(kind='bar', ylim=(-1.0,1.0), rot=0, colormap='summer_r', width=0.7, figsize=(15,5), yticks=[-1.0,-0.5,0,0.5,1.0], xlabel='cluster', ylabel='survival rate')
    plt.legend(labels=[x.split('_',2)[1]+' \u03BCM' for x in df.columns], loc='center left', bbox_to_anchor=(1.0, 0.5))
    plt.title(index_list[0].split('_',1)[0], fontweight='bold')
    plt.axhline(y=0, color='black', linestyle='-', lw=0.8)
    plt.axhline(y=threshold, color='red', linestyle='dotted', lw=0.8)
    plt.text((n_c:=len(df_effect.columns))-0.3, threshold+0.01, 'threshold={}'.format(threshold), fontsize=8, color='red')
    plt.axhline(y=conthreshold, color='blue', linestyle='dotted', lw=0.8)
    plt.text(n_c-0.3, conthreshold+0.01, 'con. threshold={}'.format(conthreshold), fontsize=8, color='blue')
    pp.savefig(bbox_inches='tight')
    plt.close()
    return df_all
    

parser = argparse.ArgumentParser(description='Generate drug effect plots and dataframe(.csv)')
parser.add_argument('-d', '--dir', required=True, help='the directory where df_effect.pickle and DICT_DRUG_PRE.pickle are stored.')
parser.add_argument('-t', '--table', required=True, help='path to the solution table (file name: \'*_solution_list_t*_cont*.csv\') generated after running treatment_selection.py.')
parser.add_argument('--threshold', default=None, help='threshold of cell survival rate used for treatment selection; If not provided, the value wll be set based on the name of the table file.')
parser.add_argument('--conthreshold', default=None, help='consistency threshold used for treatment selection; If not provided, the value wll be set based on the name of the table file.')
parser.add_argument('--names', default=None, help='comma-delimited names of drugs for heatmap visualization. Example: palbociclib,NVP-BEZ235,selumetinib')

args = parser.parse_args()

if not os.path.isdir(args.dir):
    sys.exit('The directory does not exist.')
if not os.path.isfile(args.table):
    sys.exit('The solution table( .csv) does not exist.')

df_effect = pd.DataFrame()
DICT_DRUG_PRE = {}
threshold = conthreshold = 0

for file in os.listdir(args.dir):
    if file.endswith('df_effect.pickle'):
        with open('{}/{}'.format(args.dir, file), 'rb') as fh:
            df_effect = pickle.load(fh)
            df_effect = df_effect.iloc[:, :int(len(df_effect.columns)/2)]
            df_effect = df_effect.reindex(sorted(df_effect.columns, key=int), axis=1)
    elif file.endswith('DICT_DRUG_PRE.pickle'):
        with open('{}/{}'.format(args.dir, file), 'rb') as fh:
            DRUG_LIST_PRE = pickle.load(fh)

if df_effect.size == 0:
    sys.exit('df_effect.pickle does not exist or is empty.')
if len(DRUG_LIST_PRE) == 0:
    sys.exit('DRUG_LIST_PRE.pickle does not exist or is empty.')

if args.threshold and args.threshold <= 1 and args.threshold >= -1 :
    threshold = args.threshold
else:
    threshold = float(args.table.rsplit('_',2)[1].rsplit('t',1)[1])
if args.conthreshold and args.conthreshold <= 1 and args.conthreshold >= -1 :
    conthreshold = args.conthreshold
else:
    conthreshold = float(args.table.rsplit('.',1)[0].rsplit('cont',1)[1])



keywords = list(set(pd.read_csv(args.table, header=None).values.flatten()))

keywords = list(set([x.split('_',1)[0] for x in keywords if isinstance(x, str) ]))
print('{} unique drugs.'.format(len(keywords)))

DICT_INDEX = {}

pdfname = 'treatment_effect.pdf'
pp = PdfPages(pdfname)
df_all = pd.DataFrame(columns = df_effect.columns)
for drug_id in sorted(keywords):
    DICT_INDEX[drug_id] = [x for x in DRUG_LIST_PRE.keys() if drug_id == x.split('_',1)[0]]
    df_all = draw_consistency_plot(DICT_INDEX[drug_id], df_effect, df_all)
pp.close()

df_all.to_csv('treatment_effect.csv', index=True)
print('Figures are stored in \'{}\' . \n Values are stored in \'treatment_effect.csv\' .'.format(pdfname))

if args.names:
    draw_heatmap(df_all, args.names.split(','))

