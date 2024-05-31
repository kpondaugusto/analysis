# -*- coding: utf-8 -*-
"""
@author: Chip Lab

Plots data fitted in heating_rates_fitting.py and theory lines from modified
Tilman code bulkvisctrap_class.py.

Relies on data_class.py, library.py, and bulkvisctrap_class.py
"""
from data_class import Data
from library import *
from UFG_analysis import BulkViscTrap, BulkViscUniform
from itertools import chain
from matplotlib import cm

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt 
import os
import pickle

ARBITRARY_RESCALING = 1
error_band = 0.14
band_alpha = 0.2

removed_files = ["2024-03-26_B_UHfit.dat",
				"2024-03-26_C_UHfit.dat",
				"2024-04-03_B_UHfit.dat",
				"2024-04-03_C_UHfit.dat",
				"2024-04-03_D_UHfit.dat",
				"2024-04-03_F_UHfit.dat",
# 				"2024-04-04_C_UHfit.dat",
				"2024-04-05_C_UHfit.dat",
				"2024-04-08_G_UHfit.dat",
				"2024-04-10_C_UHfit.dat",
				"2024-04-10_D_UHfit.dat"
# 				"2024-03-19_L_UHfit.dat",
# 				"2024-04-03_F_UHfit.dat",
				"2024-05-09_M_UHfit.dat"
				]

removed_names = ["2024-03-21_B_f=75_Vpp=0.25",
				 "2024-03-21_D_f=15_Vpp=0.40",
				"2024-04-03_F_f=1_Vpp=1.80", 
				 "2024-04-03_F_f=2_Vpp=1.80",
				 "2024-04-08_G_f=20_Vpp=1.80"]

data_folder = 'data//heating'
pkl_filename = 'heating_rate_fit_results.pkl'
pkl_file = os.path.join(data_folder, pkl_filename)

BVT_pkl_filename = 'BVT.pkl'
BVT_pkl_file = os.path.join(data_folder, BVT_pkl_filename)

TilmanPRL0p58ToTF_filename = "zetaomega_T0.58.txt"

plot_legend = True
load_theory = True # load Tilman lines from previous evaluation
debugging_plots = False

# only use up to max freq
nu_min = 1
nu_max = 140

def mutrap_est(ToTF):
	a = -70e3
	b = 36e3
	return a*ToTF + b

def zeta_from_C(freq, C, EF):
	"""See OverLeaf note"""
	pi_factors = (4*pi)**(3/2)/(36*pi*(2*pi)**(3/2))
	return pi_factors * (EF/freq)**(3/2) * C

def Edot_from_C(freq, C, EF):
	"""See OverLeaf note"""
	pi_factors = (4*pi)**(3/2)/(36*pi*(2*pi)**(3/2))
	return pi_factors * (EF/freq)**(3/2) * C

def zeta_from_phase(freq, EF, phase, sumrule):
	"""See OverLeaf note"""
	return EF/freq*sumrule*np.tan(phase)

############ LOAD DATA ############
try: # open pkl file if it's there
	with open(pkl_file, 'rb') as f:
		lr = pickle.load(f) # load all results in file
except FileNotFoundError: # if file not there then complain
	print("Can't find data results pickle file, you silly billy.")

########### LOAD THEORY ###########
### Run tilman's code for each Theta and EF, dumping result into pickle file
if load_theory == True:
	with open(BVT_pkl_file, 'rb') as f:  
		BVTs = pickle.load(f)
else:
	BVTs = []

############## PLOTTING ##############		
# change matplotlib options
plt.rcParams.update(plt_settings)
plt.rcParams.update({"figure.figsize": [12,8]})
fig, axs = plt.subplots(4,2)

###
### Scaled heating rate data compared to theory (First Column)
###

# select frequencies within a band.
lr = lr[lr.freq <= nu_max]
lr = lr[lr.freq >= nu_min]

# other selection criteria
lr = lr[lr.filename.isin(removed_files) == False] # WTF pandas
lr = lr[lr.index.isin(removed_names) == False] # WTF pandas

# Parameter sets to group color and marker by
eps = 1e-3
EF_range_16 = [13,17] # kHz
# EF_range_14 = [13,14.99] # kHz
EF_range_12 = [11,13-eps] # kHz
ToTF_range_0p5 = [0.45, 0.55-eps]
ToTF_range_0p6 = [0.55, 0.65-eps]
ToTF_range_0p7 = [0.65, 0.75-eps]
range_names = ['EF', 'ToTF']
param_sets = np.array([[EF_range_16, ToTF_range_0p5],[EF_range_16, ToTF_range_0p6],
					   [EF_range_12, ToTF_range_0p7]])

num = int(nu_max/nu_min)
nus = np.linspace(nu_min*1e3, nu_max*1e3, num)

label_Drude = 'Drude'
label_LW = 'L-W'
label_Qcrit = r'$\arctan(\frac{\omega\tau} {1+\omega^2\tau^2})$'
label_C = 'Contact'
	
ax = axs[0,1]
ylabel = "Heating Rate $h \\langle\dot{E}\\rangle/(E_F\\,A)^2$"
xlabel = "Drive Frequency $\hbar\omega/E_F$"
ax.set(ylabel=ylabel, xlabel=xlabel)

ax_res = axs[1,0]
ylabel = "Measurement/Theory"
ax_res.set(ylabel=ylabel, xlabel=xlabel)

ax_zeta = axs[0,0]
ylabel = "Contact Correlation $\\langle\\tilde{\zeta}(\omega)\\rangle $"
xlims = [0.05, 15] # omega/EF
ax_zeta.set(xlabel=xlabel, ylabel=ylabel, yscale='log', xscale='log', xlim=xlims)

ax_EdotSus = axs[1,1]
ylabel = "$h \\langle\dot{E}\\rangle/(E_F\\,A)^2 / \\langle \\tilde{S} \\rangle$"
xlabel = "Drive Frequency $\hbar\omega/E_F$"
xlims=[0,2]
ylims=[-0.1,0.9]
ax_EdotSus.set(ylabel=ylabel, xlabel=xlabel, xlim=xlims, ylim=ylims)

ax_EdotCon = axs[3,1]
ylabel = "$h \\langle\dot{E}\\rangle/(E_F\\,A)^2 / \\langle \\tilde{C} \\rangle$"
xlabel = "Drive Frequency $\hbar\omega/E_F$"
xlims=[1,10]
ax_EdotCon.set(ylabel=ylabel, xlabel=xlabel, xlim=xlims)

ax_ps = axs[2,0]
ylabel = "$tan^{-1} h \\langle\dot{E}\\rangle/(E_F\\,A)^2  / \\langle \\tilde{S} \\rangle / \omega$"
xlabel = "$\omega/T$"
ylims=[-0.1,0.7]
ax_ps.set(xlabel=xlabel, ylabel=ylabel, xscale='log', ylim=ylims)

ax_ps2 = axs[2,1]
ylabel = "$\phi$ from Tan's C"
xlabel = "$\omega/T$"
ylims=[-0.1,0.7]
ax_ps2.set(xlabel=xlabel, ylabel=ylabel, xscale='log', ylim=ylims)
# doesn't do anything right now
# ax_res_zeta = axs[2,0]
# ylabel = "$a^2 \zeta$ Meas./Theory"
# xlabel = "Drive Frequency (kHz)"
# # 	xlims = [0.05, 15] # omega/EF
# ax_res_zeta.set(xlabel=xlabel, ylabel=ylabel)

### Heating rate measurements
loops = len(param_sets) # to count over to pull the right theory curve if loading
used_colors = []
Tmeans = []
for param_set, color, marker, i in zip(param_sets, colors, markers, range(loops)):
	# non-zero rates for log plotting
	df = lr.loc[lr['rate']-lr['e_rate'] > 0]
	df = df.loc[df['rate']> 0]
	
	# selection dataset from df
	for name, j in zip(range_names, range(len(range_names))):
		df = df.loc[df[name] > param_set[j,0]]
		df = df.loc[df[name] < param_set[j,1]]
	
	print(df.head())
	xx = np.array(df.freq)
	yy = np.array(df.rate)
	yerr = np.array(df.e_rate)
	Ei = np.array(df.Ei)
	EF = np.array(df.EF)
	T = np.array(df["T"]) # T is a terrible column name
	ToTF = np.array(df.ToTF)
	zetas = np.array(df.zeta)
	e_zetas = np.array(df.e_zeta) # just scales with the other params in the same way
	Cas = np.array(df.Ca)
	As = np.array(df.A)
	adbsinphi = 4*pi*yy/xx/EF/As/Cas * EF**2*As**2 # heating rate yy is already normalized by (EF*A)**2, have to remove it
	mean_df = df.groupby('filename').mean(numeric_only=True) # had to do this for pandas 2.1.1
	barnu = float((mean_df.wx.mean()*mean_df.mean().wy*mean_df.wz.mean())**(1/3))
	EFmean = float(mean_df.EF.mean())
	ToTFmean = float(mean_df.ToTF.mean())
	Tmean = ToTFmean*EFmean
	
	used_colors.append(color)
	Tmeans.append(Tmean)
	
# 	print(ToTF, EF, barnu)
	
# 	label = r'[{}_{}]  $E_F={:.1f}$kHz, $T/T_F={:.2f}$, $\bar \nu={:.0f}$Hz'.format(df.date.values[0], 
# 								  df.run.values[0], EFmean, ToTFmean, barnu)
	
	label = r'$E_F={:.1f}$kHz, $T/T_F={:.2f}$, $\bar \nu={:.0f}$Hz'.format(EFmean, 
															ToTFmean, barnu)
	
	# trap $\bar\omega={:.0f}$Hz, 
	light_color = tint_shade_color(color, amount=1+tintshade)
	dark_color = tint_shade_color(color, amount=1-tintshade)
	
	ax.errorbar(xx/EF, yy, yerr=yerr, capsize=0, fmt=marker, 
			 color=dark_color, markerfacecolor=light_color, 
			 markeredgecolor=dark_color, markeredgewidth=2)
	
	ax_zeta.errorbar(xx/EF, zetas, yerr=e_zetas, capsize=0, fmt=marker,
			  color=dark_color, markerfacecolor=light_color, 
			  markeredgecolor=dark_color, markeredgewidth=2)
	
	# Edot over Scale sus
	# these values were taken from a Contact Correlations slide
	dCdkFainvlow = 1.56 - 0.23
	dCdkFainvhigh = 1.56 + 0.23
	scalesuslow = dCdkFainvlow/(18*pi) # dimensionless scale sus
	scalesushigh = dCdkFainvhigh/(18*pi)
	dCdkFainv = 1.56
	scalesus = dCdkFainv/(18*pi)
	ax_EdotSus.errorbar(xx/EF, yy/scalesus, yerr=yerr/scalesus, capsize=0, fmt=marker, 
						color=dark_color, mfc=light_color, 
						mec=dark_color, mew=2)
	# Edot over Contact
	Cmeas = 0.78 # hard-coded...
	ax_EdotCon.errorbar(xx/EF, yy/Cmeas, yerr=yerr/Cmeas, capsize=0, fmt=marker, 
						color=dark_color, mfc=light_color, 
						mec=dark_color, mew=2)
	# phase shifts
	ax_ps.errorbar(xx/T, np.arctan(yy/scalesus/xx*EF), capsize=0, fmt=marker, color=dark_color, mfc=light_color, mec=dark_color, mew=2)
	ax_ps2.errorbar(xx/T, np.arcsin(adbsinphi), capsize=0, fmt=marker, color=dark_color, mfc=light_color, mec=dark_color, mew=2)

### Heating rate theory line(s)
	if load_theory == False:
		print("Computing theory curve for ToTF={:.2f}".format(ToTFmean))
		params_trap = [Tmean*1e3, barnu, -3800] # give T, barnu and mutrap_guess in Hz
		BVT = BulkViscTrap(*params_trap, nus, ToTF=ToTFmean)
		BVTs.append(BVT)
		print("Computation complete.")
	else:
		BVT = BVTs[i]
	
	# find nus for nu/EF > 1 to use for high_freq
	if load_theory == False: print('find nus')
	nu_small = 0
	for nu in nus:
		if nu < (3*BVT.T):
			nu_small += 1
	
	nusoEF = BVT.nus/BVT.EF
	Edotnorm = (2*BVT.Ns) * (BVT.EF**2)
	# plot Drude form if small frequencies exist
	if load_theory == False: print('plot Drude')
	if xx.min() < 2*Tmean:
		Edots = BVT.Edottraps/Edotnorm
		ax.plot(nusoEF[:nu_small], Edots[:nu_small], ':', color=color, label=label_Drude)
		ax.fill_between(nusoEF[:nu_small], Edots[:nu_small]*(1 - error_band), 
					 Edots[:nu_small]*(1 + error_band), alpha=band_alpha, color=color)
		
		ax_zeta.plot(nusoEF[:nu_small], BVT.zetatraps[:nu_small],':', color=color, label=label_Drude)
		ax_zeta.fill_between(nusoEF[:nu_small], BVT.zetatraps[:nu_small]*(1 - error_band), 
			  BVT.zetatraps[:nu_small]*(1 + error_band), alpha=band_alpha, color=color)
		
		ax_EdotSus.plot(nusoEF[:nu_small], BVT.EdottrapsS[:nu_small]/BVT.Etotal, ':', color=color, label=label_Drude)

	# plot contact determined lines if large frequencies exist
	if load_theory == False: print('plot contact')
	if xx.max() > 2*Tmean:
		Edots = BVT.EdottrapsC/Edotnorm
		ax.plot(nusoEF[nu_small:], Edots[nu_small:],'--', color=color, label=label_C)
		ax.fill_between(nusoEF[nu_small:], Edots[nu_small:]*(1 - error_band), 
		 Edots[nu_small:]*(1 + error_band), alpha=band_alpha, color=color)
		ax_zeta.plot(nusoEF[nu_small:], BVT.zetatrapsC[nu_small:],'--', 
				  color=color, label=label_C)
		ax_zeta.fill_between(nusoEF[nu_small:], BVT.zetatrapsC[nu_small:]*(1 - error_band), 
			  BVT.zetatrapsC[nu_small:]*(1 + error_band), alpha=band_alpha, color=color)
		
		ax_EdotCon.plot(nusoEF[nu_small:], BVT.EdottrapsNormC[nu_small:]/BVT.Etotal, '--',color=color, label=label_C)
		ax_EdotCon.plot(nusoEF[nu_small:], BVT.EdottrapsNormC[nu_small:]/BVT.Etotal*4, '-.',color=color, label='4*Contact')
		# factor of 4 lmao how
	# does this work?...
	ax_ps.plot(nus/BVT.T, BVT.phaseshiftsQcrit, '--', color=color, label=label_Qcrit)
	ax_ps2.plot(nus/BVT.T, BVT.phaseshiftsQcrit, '--', color=color, label=label_Qcrit)
### Residual ratio
	residuals = []
	e_res = []
	residuals_zeta = []
	e_res_zeta = []
	for freq, rate, e_rate, zeta, e_zeta in zip(xx, yy, yerr, zetas, e_zetas):
		for j in range(len(BVT.nus)):
 			if BVT.nus[j]/1e3 == freq:
				 if BVT.nus[j] < 2*BVT.T:
	 				 residuals.append(rate/(BVT.Edottraps[j]/Edotnorm))
	 				 residuals_zeta.append(zeta/BVT.zetatraps[j])
	 				 e_res.append(e_rate/(BVT.Edottraps[j]/Edotnorm))
	 				 e_res_zeta.append(e_zeta/BVT.zetatraps[j])
				 else: 
	 				 residuals.append(rate/(BVT.EdottrapsC[j]/Edotnorm))
	 				 residuals_zeta.append(zeta/BVT.zetatrapsC[j])
	 				 e_res.append(e_rate/(BVT.EdottrapsC[j]/Edotnorm))
	 				 e_res_zeta.append(e_zeta/BVT.zetatrapsC[j])
				 continue
 	
	ax_res.errorbar(xx, np.array(residuals), yerr=e_res, capsize=0, fmt=marker, 
			  label=label, color=dark_color, markerfacecolor=light_color, 
			  markeredgecolor=dark_color, markeredgewidth=2)
	
### Legends for theory curves
	print(i)
	print(BVT.Ctrap)
	if i == 0:
		ax.legend()
		ax_zeta.legend()
		ax_EdotSus.legend()
		ax_EdotCon.legend()
		ax_ps.legend()
		ax_ps2.legend()
		
# set dashed line to illustrate change from Drude to Contact
ymin, ymax = ax_res.get_ylim()
Tline = np.mean(Tmean)
ax_res.vlines(2*Tline, 0, ymax, colors='grey')
ax_res.set(ylim=[0,ymax])


### Add contact line
C = 0.78
e_C = 0.01
EF = 16e3
C_theory = 1.465
ax_zeta.plot(nus[nu_small:]/EF, zeta_from_C(nus, C, EF)[nu_small:],'k--',
		 label='$\\langle\\tilde{C}\\rangle = 0.78(1)$ from HFT spectroscopy')

ax_res.plot(nus[nu_small:]/1e3, C/C_theory*np.ones(len(nus[nu_small:])),'k--',
		 label='$\\langle\\tilde{C}\\rangle = 0.78(1)$ from HFT spectroscopy')

### Add tabulated Tilman 0.58ToTF line from PRL
xtilman, ytilman = np.loadtxt(TilmanPRL0p58ToTF_filename, unpack=True, delimiter=' ')

	

### Manually add measured phase shift 
dCdkFainv = 1.5
sumrule = dCdkFainv/(18*pi) # dimensionless scale sus
EF = 16
ToTF = 0.56
T = ToTF*EF
freqs = np.array([2, 5])
phases = np.array([-0.06, 0.35])
phases_err = np.array([0.09, 0.06])

zetas_phase = np.array([zeta_from_phase(freq, EF, phase, sumrule) \
						for freq, phase in zip(freqs, phases)])
zetas_phase_err = np.array([zeta_from_phase(freq, EF, phase, sumrule) \
			for freq, phase in zip(freqs, phases+phases_err)]) - zetas_phase

color = colors[1]
marker = '^'
light_color = tint_shade_color(color, amount=1+tintshade)
dark_color = tint_shade_color(color, amount=1-tintshade)
ax_zeta.errorbar(freqs/EF, zetas_phase, yerr=zetas_phase_err, capsize=0, 
				 fmt=marker, color=dark_color, markerfacecolor=light_color, 
			 markeredgecolor=dark_color, markeredgewidth=2)

label_phase = r"Phase Shift: $E_F = 16$kHz, $T/T_F = 0.56$"

freq_indices = [1, 4] # 2 kHz and 5 kHz
BVT = BVTs[0] # ToTF = 0.50
residuals = zetas_phase/BVT.zetatraps[freq_indices]
e_res = zetas_phase_err/BVT.zetatraps[freq_indices]
ax_res.errorbar(freqs, residuals, yerr=e_res, capsize=0, fmt=marker, 
			  label=label_phase, color=dark_color, markerfacecolor=light_color, 
			  markeredgecolor=dark_color, markeredgewidth=2)

# add phase shift measurements to phi plots
ax_ps.errorbar(freqs/T, phases, yerr=phases_err, capsize=0, fmt=marker, label=label_phase,
				color=dark_color, mfc=light_color, mec=dark_color, mew=2)

ax_ps2.errorbar(freqs/T, phases, yerr=phases_err, capsize=0, fmt=marker, label=label_phase,
				color=dark_color, mfc=light_color, mec=dark_color, mew=2)

###
### Legend in own subplot
###
if plot_legend:
	lax = axs[3,0]
	h, l = ax_res.get_legend_handles_labels() # get legend from first plot
	lax.legend(h, l, borderaxespad=0)
	lax.axis("off")

	
fig.tight_layout()
fig.savefig("figures/summary.pdf")
plt.show()

########### SAVE THEORY ###########
if load_theory == False:
	with open(BVT_pkl_file, 'wb') as f:  
		pickle.dump(BVTs, f)
		
