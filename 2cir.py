'''

このコードは北斗電工SD8による充放電測定結果csvを入力とします。
cd_patern, ir_paternにパターン名を整数で指定してください、そしてcicle_listにプロットしたいサイクル数を整数のリストで指定してください。
SD8の新型と旧型の差による変更はmap_to_rawdata関数内の列数を調整して行ってください。
IR測定の設定によってget_ir_points関数内を調整してください。
このコードによる出力は以下の通りです。必要に応じてmain関数を書き換えてください。
1.internal resistanceのプロット画像をoutput_path_figに
2.Charge and Discharge carve 画像をoutput_path_figに
3.Sma4への入力のために最適化したcsvをoutput_path_rstに
4.各種設定や測定値の辞書param_dicをoutput_path_rstにあるedithistory.csvに更新履歴として保存
5.生データのcsvをoutput_path_rawにリネームして移動

This code takes as input the csv of charge/discharge measurement results by Hokuto Electric SD8.
Specify the pattern name as an integer in cd_patern and ir_patern, and the number of cycles to be plotted in cicle_list as a list of integers.
If you account for the difference between the newer and older SD8 models, adjust the number of rows in the map_to_rawdata function.
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

class RawData():
    def __init__(self,V,I,Cap,Cicle,Step,Mode,Patern):
        self.V = float(V)
        self.I = float(I)
        self.Cap = float(Cap)
        self.Cicle = int(Cicle)
        self.Step = int(Step)
        self.Mode = Mode    # str
        self.Patern = int(Patern)

class Sma4DataTable():
    def __init__(self,label,data):
        self.label = label  # str
        self.data = data    # []float

# record detaile param
JST = timezone(timedelta(hours=+9), 'JST')
param_dic =  {'timestamp':str(datetime.now(JST)),
        'sample ID':"empty",
        'active material mass(mg)':"empty",
        'discharge capacity(mAh/g)':0,
        'IR(k ohm)':0,
        'remarks':"empty",
        'oxidation degree':0,
        'memo':"",
        'others':""}

def main():
    files = glob.glob(import_path+"*.csv")
    raw_data_file_name = files[0]
    print(raw_data_file_name)

    rawdata2D = []
    ln_cnt = 0
    with open(raw_data_file_name) as f:
        for line in f:  # read line by line.
            if ln_cnt < 18: 
                map_param_to_dic(param_dic, line, ln_cnt)
            else:
                rawdata2D.append(map_to_rawdata(line))
            ln_cnt += 1
    # so far input.
    # check input here.
    # for i in range(len(rawdata2D)):
    #     print(rawdata2D[i].V, rawdata2D[i].I, rawdata2D[i].Cap )

    sma4data2D = makeSma4Table(rawdata2D,cd_patern,cicle_list)

    param_dic["discharge capacity(mAh/g)"] = round(get_maxcap_in_discharge(rawdata2D, cd_patern, cicle_list), 4)
    param_dic["oxidation degree"] = round(calc_oxidation_degree(sma4data2D), 4)

    output_file_name = param_dic["sample ID"]+"_"+param_dic["remarks"]

    if exist_ir_patern(rawdata2D, ir_patern):
        Currents,dVs = get_ir_points(rawdata2D, ir_patern)
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
    with open(output_path_rst + output_file_name + '_forsma4.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(convert_Table_to_2dlist(sma4data2D))
    
    # reflect to result edithistory.csv.
    headersCSV = ['timestamp','sample ID','active material mass(mg)','discharge capacity(mAh/g)','IR(k ohm)','remarks','oxidation degree','memo','others']      
    # First, open the old CSV file in append mode, hence mentioned as 'a'.Then, for the CSV file, create a file object
    with open(output_path_rst+'edit_history.csv', 'a', newline='') as f_object:
        dictwriter_object = DictWriter(f_object, fieldnames=headersCSV)
        dictwriter_object.writerow(param_dic)
        f_object.close()

    # move raw data csv to specified directory.
    os.rename(raw_data_file_name , output_path_raw + output_file_name+'_rawdata.csv')

    print("finished.")

    return

def map_param_to_dic(param_dic, lin, ii):
    indb = lin.split(",")
    if ii == 4:
        param_dic["remarks"] = indb[1]
    elif ii == 7:
        param_dic["sample ID"] = indb[1]
        print("sample name:",indb[1])
    elif ii ==12:
        param_dic["active material mass(mg)"] = indb[1]
    return

def map_to_rawdata(lin):
    indd = lin.split(",")
    # "V-1  mAh/g-5  cicle-10  mode-12  patern-13" value cast       V,I,Cap,Cicle,Step,Mode,Patern
    data = RawData(V=indd[1],I=indd[2],Cap=indd[5],Cicle=indd[10],Step=indd[11],Mode=indd[12],Patern=indd[13])
    return data

def makeSma4Table(rdt, cd_patern, cicle_list):
    table = []
    for ci in cicle_list:
        ccs = []    # capacity and charge list
        vcs = []    # voltage and discharge list
        cds = []
        vds = []
        for j in range(len(rdt)):
            if rdt[j].Patern == cd_patern:
                if rdt[j].Cicle == ci and rdt[j].Mode == "Charge":
                    ccs.append(rdt[j].Cap)
                    vcs.append(rdt[j].V)
                if rdt[j].Cicle == ci and rdt[j].Mode == "Discharge":
                    cds.append(rdt[j].Cap)
                    vds.append(rdt[j].V)
        p1 = Sma4DataTable(label = str(ci)+"_Charge_mAh/g",data = ccs)
        p2 = Sma4DataTable(label = str(ci)+"_Charge_V",data = vcs)
        p3 = Sma4DataTable(label = str(ci)+"_Discharge_mAh/g",data = cds)
        p4 = Sma4DataTable(label = str(ci)+"_Discharge_V",data = vds)
        table.append(p1)
        table.append(p2)
        table.append(p3)
        table.append(p4)
    return table

def get_maxcap_in_discharge(rdt, cd_patern, cd_list):
    maxcap = 0.0
    for ci in cicle_list:
        for ii in range(len(rdt)):
            if rdt[ii].Patern == cd_patern and rdt[ii].Cicle == ci and rdt[ii].Mode == "Discharge":
                    if maxcap < rdt[ii].Cap:
                        maxcap = rdt[ii].Cap
    return maxcap

def calc_oxidation_degree(s4d):
    # rate of  1st charge cap and 2nd charge cap
    if len(s4d) < 4:
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

def exist_ir_patern(rdt, ir_patern):
    rsp = False
    for pp in range(len(rdt)):
        if rdt[pp].Patern == ir_patern:
            rsp = True
            break
    return rsp

def get_ir_points(data2d, ir_patern):
    I_list = []     # microA (<- mA)
    deltaV_list = []     # mV (<- V)
    for i in range(len(data2d)):
        if data2d[i].Patern == ir_patern:
            if  data2d[i].Mode == "Rest" and data2d[i-1].Mode == "Charge":  # find border of Mode
                if data2d[i-1].Step != 1:
                    # ignoring the first voltage adjusting process!!!! note!!!!
                    deltaV_list.append(abs(data2d[i-1].V - data2d[i+1].V) * 1000)
                    I_list.append(abs(data2d[i].I * 1000))
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
                
if __name__ == "__main__":
    # plot line colors
    color_list=['red','#ff6347','#00fa9a','#87ceeb','#0000cd','#ffa500','#ffdab9','#808000','#228b22','#228b22']
    label_dic={1:'1st cicle',2:'2nd cicle', 3:'3rd cicle' , 4:'4th cicle',5:'5th cicle',
            6:'6th cicle',7:'7th cicle',8:'8th cicle',9:'9th cicle',10:'10th cicle',20:'20th cicle',
            50:'50th cicle',100:'100th cicle'}
    main()
