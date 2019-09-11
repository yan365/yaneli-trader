# -*- coding: utf-8 -*-

def save_data(dataframe, output_filename='out.csv', sep=',', **kwargs):
    args = {
            'path_or_buf':output_filename,
            'sep':sep,
            'header':True,
            'index':False,
            }
    args.update(kwargs)
    dataframe.to_csv(**args)

def plot_data(dataframe, y_axis='close', **kwargs):
    args = {
            'y':y_axis,
            }
    args.update(kwargs)
    fig = dataframe.plot(**args)
    fig.figure.show()
    util.barplot(dataframe)
