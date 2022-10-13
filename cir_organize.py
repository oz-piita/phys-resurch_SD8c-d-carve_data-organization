'''

このコードは北斗電工SD8による充放電測定結果csvを入力とします。
表示項目は時間、電圧、電流、電力、Ah(Step)、Ah/g(Step)、Wh(Step)、Wh/g(Step)、サイクル時間、ステップ時間、サイクル、ステップ、モード、パターン名です。
cd_patern, ir_paternにパターン名を整数で指定してください、そしてcicle_listにプロットしたいサイクル数を整数のリストで指定してください。
IR測定の設定によってget_ir_points関数内を調整してください。
このコードによる出力は以下の通りです。必要に応じてmain関数を書き換えてください。
1.internal resistanceのプロット画像をoutput_path_figに
2.Charge and Discharge carve 画像をoutput_path_figに
3.Sma4への入力のために整列したcsvをoutput_path_rstに
4.各種設定や測定値の辞書param_dicをoutput_path_rstにあるedithistory.csvに更新履歴として保存
5.生データのcsvをoutput_path_rawにリネームして移動

This code takes as input the csv of charge/discharge measurement results by Hokuto Electric SD8.
Specify the pattern name as an integer in cd_patern and ir_patern, and the number of cycles to be plotted in cicle_list as a list of integers.
According to your IR measurement settings, adjust the get_ir_points function.
The output from this code is as follows. Rewrite the main function as necessary.
1. plot image of internal resistance to output_path_fig
2. Charge/Discharge carves image to output_path_fig
3. csv optimized for input to Sma4 to output_path_rst
4. dictionary param_dic of various settings and measurements saved as update history in edithistory.csv in output_path_rst
5. rename and move raw data csv to output_path_raw

'''

import glob
from datetime import datetime,timedelta,timezone
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import csv
from csv import DictWriter
import os

cd_patern = 2       # patern name who draws charge&discharge carve
ir_patern = 1       # patern name which measures IR
cicle_list = [1, 2]  # cicle number which you wanna plot

# path
import_path = './untreated/'
output_path_rst = './result/'
output_path_fig = './figure/'
output_path_raw = './rawdata/'

class Sma4DataTable():
    def __init__(self,label,data):
        self.label = label   # str
        self.data  = data    # []float

# record detaile param
JST = timezone(timedelta(hours=+9), 'JST')
param_dic =  {'timestamp'          :str(datetime.now(JST)),
        'sample ID'                :"empty",
        'active material mass(mg)' :"empty",
        'discharge capacity(mAh/g)':0,
        'IR(k ohm)'                :0,
        'remarks'                  :"empty",
        'oxidation degree'         :0,
        'memo'                     :"",
        'others'                   :""}

def main():
    files = glob.glob(import_path+"*.csv")
    raw_data_file_name = files[0]
    print(raw_data_file_name)

    map_param_to_dic(raw_data_file_name, param_dic)
    rdf = pd.read_csv(raw_data_file_name, encoding="shift-jis", header=None, skiprows=17)
    rdf = rdf.drop([0,3,4,6,7,8,9], axis = 1).rename(columns = raw_dataframe_colnames_dic)
    # so far input.
    # print(rdf)      # check here.

    sma4data2D = makeSma4Table(rdf, cd_patern, cicle_list)
    
    param_dic["discharge capacity(mAh/g)"] = round(get_maxcap_in_discharge(rdf, cd_patern, cicle_list), 4)
    param_dic["oxidation degree"] = round(calc_oxidation_degree(sma4data2D), 4)

    output_file_name = param_dic["sample ID"]+"_"+param_dic["remarks"]

    if ir_patern in rdf["Patern"].values:
        Currents,dVs = get_ir_points(rdf, ir_patern)
        ir,seg = calc_ir(Currents,dVs)
        print(ir,seg)
        param_dic["IR(k ohm)"] = round(ir, 4)
        plot_IR_scatter(Currents,dVs,ir,seg)
        plt.savefig(output_path_fig + output_file_name+'_irfig.jpg',dpi=144)        # output
        plt.show()
        plt.close()

    plot_carves(sma4data2D, cicle_list)
    plt.savefig(output_path_fig+output_file_name+'_carvefig.jpg',dpi=144)       # output
    plt.show()
    plt.close()

    # output
    make_sma4csv(sma4data2D, output_path_rst, output_file_name)
    
    save_updateLog_to_csv(param_dic, output_path_rst)

    # move raw data csv to specified directory.
    os.rename(raw_data_file_name , output_path_raw + output_file_name+'_rawdata.csv')

    print("finished.")
    return

def map_param_to_dic(raw_data_file_name, param_dic):
    ln_cnt = 0
    with open(raw_data_file_name) as f:
        for line in f:  # read line by line.
            indb = line.split(",")
            if ln_cnt == 4:
                param_dic["remarks"] = indb[1].replace("\n","").replace('"','')
            elif ln_cnt == 7:
                param_dic["sample ID"] = indb[1].replace("\n","").replace('"','')
                print("sample name:",indb[1].replace("\n","").replace('"',''))
            elif ln_cnt ==12:
                param_dic["active material mass(mg)"] = indb[1].replace("\n","")
            elif 18 <= ln_cnt:
                break
            ln_cnt += 1
    return

def makeSma4Table(rdf, cd_patern, cicle_list):
    table = []
    for ci in cicle_list:
        ccs = list(rdf[(rdf["Cicle"]== ci)&(rdf["Mode"]== "Charge")&(rdf["Patern"] == cd_patern)]["Cap"])
        vcs = list(rdf[(rdf["Cicle"]== ci)&(rdf["Mode"]== "Charge")&(rdf["Patern"] == cd_patern)]["V"])
        cds = list(rdf[(rdf["Cicle"]== ci)&(rdf["Mode"]== "Discharge")&(rdf["Patern"] == cd_patern)]["Cap"])
        vds = list(rdf[(rdf["Cicle"]== ci)&(rdf["Mode"]== "Discharge")&(rdf["Patern"] == cd_patern)]["V"])
        p1 = Sma4DataTable(label = str(ci)+"_Charge_mAh/g",data = ccs)
        p2 = Sma4DataTable(label = str(ci)+"_Charge_V",data = vcs)
        p3 = Sma4DataTable(label = str(ci)+"_Discharge_mAh/g",data = cds)
        p4 = Sma4DataTable(label = str(ci)+"_Discharge_V",data = vds)
        table.append(p1)
        table.append(p2)
        table.append(p3)
        table.append(p4)
    return table

def get_maxcap_in_discharge(rdf, cd_patern, cd_list):
    maxcap = 0.0
    for ci in cicle_list:
        if not ci in rdf[rdf["Mode"]=="Dischage"]["Cicle"].values:
            break
        candidate =  max(rdf[(rdf["Cicle"]== ci)&(rdf["Mode"]== "Discharge")&(rdf["Patern"] == cd_patern)]["Cap"])
        if maxcap < candidate:
            maxcap = candidate
    return maxcap

def calc_oxidation_degree(s4d):
    # rate of  1st charge cap and 2nd charge cap
    if len(s4d[0].data) == 0 or len(s4d[4].data) == 0:
        return 0.0
    od = 1 - max(s4d[0].data) / max(s4d[4].data)
    return od

def plot_carves(sm4, cicle_list):
    # plot charge and discharge carves
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.figure(figsize=(14, 4.5))
    plt.rcParams["font.size"] = 16
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"

    for ci in cicle_list:
        for ii in range(len(sm4)):
            if sm4[ii].label == str(ci)+"_Charge_mAh/g":
                x = sm4[ii].data
            if sm4[ii].label == str(ci)+"_Charge_V":
                y = sm4[ii].data
                plt.subplot(121)
                plt.plot(x, y, linewidth=1, color=color_list[ii//4], label=label_dic[ci])
    plt.xlabel('Capacity(mAh/g)')
    plt.ylabel('$\it{V}$(V vs. Ag/AgCl)')
    plt.yticks([0.4, 0.6, 0.8,1,1.2])

    for ci in cicle_list:
        for ii in range(len(sm4)):
            if sm4[ii].label == str(ci)+"_Discharge_mAh/g":
                x = sm4[ii].data
            if sm4[ii].label == str(ci)+"_Discharge_V":
                y = sm4[ii].data
                plt.subplot(122)
                plt.plot(x, y, linewidth=1, color=color_list[ii//4], label=label_dic[ci])
    plt.xlabel('Capacity(mAh/g)')
    plt.ylabel('$\it{V}$(V vs. Ag/AgCl)')
    plt.yticks([0.4, 0.6, 0.8,1,1.2])

    plt.legend(fontsize=13)
    plt.tight_layout()
    return

def get_ir_points(rdf, ir_patern):
    I_list = []     # microA (<- mA)
    deltaV_list = []     # mV (<- V)
    for i in rdf.index:
        if rdf["Patern"][i] == ir_patern:
            if rdf["Mode"][i] == "Rest" and rdf["Mode"][i-1] == "Charge":   # find border of Mode
                if rdf["Step"][i-1] != 1:   # ignoring the first voltage adjusting process!!!! note!!!!
                    deltaV_list.append(abs(rdf["V"][i-1] - rdf["V"][i+1]) * 1000)
                    I_list.append(abs(rdf["I"][i] * 1000))
    I_list = np.array(I_list)
    deltaV_list = np.array(deltaV_list)
    return I_list, deltaV_list

def calc_ir(i_list, deltav_list):
    ir, seg = reg1dim(i_list, deltav_list)
    return ir, seg

def abs (x):
    if x < 0:
        return -x
    else:
        return x

def reg1dim(x, y):      # least-square method
    n = len(x)
    a = ((np.dot(x, y)- y.sum() * x.sum()/n)/
        ((x ** 2).sum() - x.sum()**2 / n))
    b = (y.sum() - a * x.sum())/n
    return a, b

def plot_IR_scatter(x,y,ir,seg):
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams["font.size"] = 16
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"

    # plot internal resistance. (scatter and approximate line.)
    plt.scatter(x, y, color="k") 
    # draw a straight line
    endpoint = 50
    if 50 < x.max():
        endpoint = x.max()
    plt.plot([0, endpoint], [seg, ir * endpoint + seg]) # draw a line from (0, b) to (max(x),ax + b)
    plt.xlabel('$\it{I}$(μA)')
    plt.ylabel('$\it{⊿V}$(mV)')
    plt.text(0,(ir * endpoint + seg)*8/10, 'Rin : '+str(round(ir,3))+"(kΩ)\nsegment: "+str(round(seg,3))+"(mV)")
    plt.tight_layout()
    return

def convert_Table_to_2dlist(tbl):
    list2d = []
    line = []
    for ii in range(len(tbl)):
        line.append(tbl[ii].label)
    list2d.append(line)
    len_list = get_data_length(tbl)
    for jj in range(max(len_list)):
        line = []
        for ii in range(len(tbl)):
            if jj < len_list[ii]:
                line.append(str(tbl[ii].data[jj]))
            else:
                line.append(str(0))
        list2d.append(line)
    return list2d
            
def get_data_length(tbl):
    lengths = []
    for ii in range(len(tbl)):
        lengths.append(len(tbl[ii].data))
    return lengths

def make_sma4csv(sma4data2D, output_paht_rst, output_file_name):
    with open(output_path_rst + output_file_name + '_forsma4.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(convert_Table_to_2dlist(sma4data2D))
    return

def save_updateLog_to_csv(param_dic, output_path):
    # reflect to result edithistory.csv.
    headersCSV = ['timestamp','sample ID','active material mass(mg)','discharge capacity(mAh/g)','IR(k ohm)','remarks','oxidation degree','memo','others']      
    # First, open the old CSV file in append mode, hence mentioned as 'a'.Then, for the CSV file, create a file object
    with open(output_path_rst+'edit_history.csv', 'a', newline='') as f_object:
        dictwriter_object = DictWriter(f_object, fieldnames=headersCSV)
        dictwriter_object.writerow(param_dic)
        f_object.close()
    return
                
if __name__ == "__main__":
    # plot line colors
    color_list=['red','#ff6347','#00fa9a','#87ceeb','#0000cd','#ffa500','#ffdab9','#808000','#228b22','#228b22']
    label_dic={1:'1st cicle',2:'2nd cicle', 3:'3rd cicle' , 4:'4th cicle',5:'5th cicle',
            6:'6th cicle',7:'7th cicle',8:'8th cicle',9:'9th cicle',10:'10th cicle',20:'20th cicle',
            50:'50th cicle',100:'100th cicle'}
    raw_dataframe_colnames_dic = {
    1:"V",
    2:"I",
    5:"Cap",
    10:"Cicle",
    11:"Step",
    12:"Mode",
    13:"Patern",}
    main()
