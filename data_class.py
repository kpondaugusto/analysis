# -*- coding: utf-8 -*-
"""
2023-10-19
@author: Chip Lab

Data class for loading, fitting, and plotting .dat
Matlab output files

Relies on functions.py
"""
import os 
from glob import glob
from library import *
from fit_functions import *
from scipy.optimize import curve_fit
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from tabulate import tabulate

file = "2023-10-19_C_e.dat"
drive = '\\\\UNOBTAINIUM\\E_Carmen_Santiago' # when using Fermium
names = ["Field", "ToTFcalc"]

# plt.style.use('plottingstyle')
plt.style.use('C:/Users/coldatoms/anaconda3/pkgs/matplotlib-base-3.2.2-py38h64f37c6_0/Lib/site-packages/matplotlib/mpl-data/stylelib/plottingstype.mplstyle')

def data1(filename):
	return  Data("2023-10-19_C_e.dat",column_names=['ToTFcalc']).data

def subtract(filename):
	data1 = Data("2023-10-19_E_e.dat",column_names=['ToTFcalc','Field']).data.groupby(['Field']).mean()
	data2 = Data("2023-10-19_C_e.dat",column_names=['ToTFcalc','Field']).data.groupby(['Field']).mean()
	data3 = Data("2023-10-19_C_e.dat",column_names=['ToTFcalc']).data
	data4 = Data("2023-10-19_E_e.dat",column_names=['ToTFcalc']).data
	subtracted_data = Data("2023-10-19_E_e.dat",column_names=['ToTFcalc']).data - (Data("2023-10-19_C_e.dat",column_names=['ToTFcalc']).data)
	field = Data("2023-10-19_E_e.dat",column_names=['Field']).data
	return pd.concat([field,subtracted_data, data3, data4], axis=1)
	
class Data:
	def __init__(self, filename, path=None, column_names=None, 
			  exclude_list=None, average_by=None, residuals=None):
		self.filename = filename
		
		if path:
			file = os.path.join(path, filename) # making manual path for the filename
		else:
			file = glob(drive + '\\Data\\2023\\*\\*\\*\\' + filename)[0] # EXTREMELY greedy
			
		self.data = pd.read_table(file, delimiter=',') # making dataframe of chosen data
		
		if column_names:
			self.data = self.data[column_names]
		if exclude_list:
			self.exclude(exclude_list)
		if average_by:
			self.group_by_mean(average_by)

	# exclude list of points
	def exclude(self, exclude_list):
		self.data.drop(exclude_list)
		
	# group by scan name, compute mean 
	def group_by_mean(self, scan_name):
		mean = self.data.groupby([scan_name]).mean().reset_index()
		std = self.data.groupby([scan_name]).std().reset_index().add_prefix("e_")
		self.avg_data = pd.concat([mean, std], axis=1)
		
# subtracting column from another 

				
# plot raw data or average
	def plot(self, names=names, label=None, axes_labels=None):
		self.fig = plt.figure()
		self.ax = plt.subplot()
		if label==None:
			label = self.filename

		if hasattr(self, 'avg_data'): # check for averaging
			self.ax.errorbar(self.avg_data[f"{names[0]}"], self.avg_data[f"{names[1]}"], 
				yerr=self.avg_data[f"e_{names[1]}"], capsize=2, marker='o', ls='',
				label=label)
		else:
			self.ax.plot(self.data[f"{names[0]}"], self.data[f"{names[1]}"],
				label = label)
			
		if axes_labels == None:
			axes_labels = [f"{names[0]}", f"{names[1]}"]
			
		self.ax.set_xlabel(axes_labels[0])
		self.ax.set_ylabel(axes_labels[1])
		self.ax.legend()
		
#residuals 
	def plot_residuals(self, fit_func, names=names, guess=None, label=None, axes_labels=None):
		self.fig = plt.figure()
		self.ax = plt.subplot()
		fit_data = np.array(self.data[names])
		func, default_guess, param_names = fit_func(fit_data)
		if guess is None:	
			guess = default_guess
		if hasattr(self, 'avg_data'): # check for averaging
			popt, pcov = curve_fit(func, self.avg_data[f"{names[0]}"], 
						  self.avg_data[f"{names[1]}"],p0=guess, 
						  sigma=self.avg_data[f"e_{names[1]}"])
		else:
			popt, pcov = curve_fit(func, self.data[f"{names[0]}"], 
						  self.data[f"{names[1]}"],p0=guess)
		residuals = self.data[f"{names[1]}"] - func( self.data[f"{names[0]}"],*popt)

		if label==None:
			label = self.filename
		self.ax.plot(self.data[f"{names[0]}"], self.data[f"{names[0]}"]*0, linestyle='-')
		if hasattr(self, 'avg_data'): # check for averaging
			self.ax.errorbar(self.avg_data[f"{names[0]}"], self.avg_data[f"{names[1]}"], 
				yerr=self.avg_data[f"e_{names[1]}"], capsize=2, marker='o', ls='',
				label=label)
		else:
			self.ax.plot(self.data[f"{names[0]}"], residuals,
				label = label)
			
		if axes_labels == None:
			axes_labels = [f"{names[0]}", f"{names[1]}"]
			
		self.ax.set_xlabel(axes_labels[0])
		self.ax.set_ylabel(axes_labels[1])
		self.ax.legend()
		
		

		
# fit data to fit_func and plot if Data has a figure
	def fit(self, fit_func, names, guess=None):
		fit_data = np.array(self.data[names])
		func, default_guess, param_names = fit_func(fit_data)
		print(default_guess)
		print(func(201.5, *default_guess))
		
		if guess is None:	
			guess = default_guess
			
		if hasattr(self, 'avg_data'): # check for averaging
			popt, pcov = curve_fit(func, self.avg_data[f"{names[0]}"], 
						  self.avg_data[f"{names[1]}"],p0=guess, 
						  sigma=self.avg_data[f"e_{names[1]}"])
		else:
			popt, pcov = curve_fit(func, self.data[f"{names[0]}"], 
						  self.data[f"{names[1]}"],p0=guess)
		perr = np.sqrt(np.diag(pcov))
		
		self.parameter_table = tabulate([['Values', *popt], ['Errors', *perr]], 
								 headers=param_names)
		print(self.parameter_table)
		
		self.plot(names, label=None, axes_labels=None)
		
		if hasattr(self, 'ax'): # check for plot
			num = 500
			xlist = np.linspace(self.data[f"{names[0]}"].min(), 
					   self.data[f"{names[0]}"].max(), num)
			self.ax.plot(xlist, func(xlist, *popt))