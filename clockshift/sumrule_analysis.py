"""
Created by Chip lab 2024-06-12

Loads .dat with contact HFT scan and computes scaled transfer. Plots. Also
computes the sumrule.

To do:
	
"""
from library import pi, h, hbar, mK, a0, plt_settings, GammaTilde, tintshade, \
				 tint_shade_color, ChipKaiser, ChipBlackman, markers, colors
from data_class import Data
from scipy.optimize import curve_fit
from clockshift.MonteCarloSpectraIntegration import MonteCarlo_spectra_fit_trapz
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import time

# paths
proj_path = os.path.dirname(os.path.realpath(__file__))
root = os.path.dirname(proj_path)
data_path = os.path.join(proj_path, 'data')

### This turns on (True) and off (False) saving the data/plots 
Saveon = True 

### script options
Analysis = True
Summaryplots = True
MonteCarlo = True

### metadata
metadata_filename = 'metadata_file.xlsx'
metadata_file = os.path.join(proj_path, metadata_filename)
metadata = pd.read_excel(metadata_file)
files =  metadata.loc[metadata['exclude'] == 0]['filename'].values

# Manual file select, comment out if exclude column should be used instead
# files = ["2024-07-03_E_e"]

# save file path
savefilename = 'sumrule_analysis_results.xlsx'
savefile = os.path.join(proj_path, savefilename)

### Vpp calibration
VVAtoVppfile = os.path.join(root,"VVAtoVpp.txt") # calibration file
VVAs, Vpps = np.loadtxt(VVAtoVppfile, unpack=True)
VpptoOmegaR = 27.5833 # kHz

def VVAtoVpp(VVA):
	"""Match VVAs to calibration file values. Will get mad if the VVA is not
		also the file. """
	Vpp = 0
	for i, VVA_val in enumerate(VVAs):
		if VVA == VVA_val:
			Vpp = Vpps[i]
	if Vpp == 0: # throw a fit if VVA not in list.
		raise ValueError("VVA value {} not in VVAtoVpp.txt".format(VVA))
	return Vpp

### contants
EF = 16e-3 # MHz
kF = np.sqrt(2*mK*EF*1e6*h)/hbar
re = 107 * a0 # ac dimer range estimate
Eb = 3.98 # MHz # I guesstimated this from recent ac dimer spectra

def a13(B):
	''' ac scattering length '''
	abg = 167.6*a0
	DeltaB = 7.2
	B0=224.2
	return abg*(1 - DeltaB/(B-B0))

def xstar(B):
	return Eb/EF * (1-re/a13(Bfield))**(-1)

def GenerateSpectraFit(xstar):
	def fit_func(x, A):
		xmax = xstar
	# 	print('xstar = {:.3f}'.format(xmax))
		return A*x**(-3/2) / (1+x/xmax)
	return fit_func

def dwSpectraFit(xi, x_star, A):
	return A*2*(1/np.sqrt(xi)-np.arctan(np.sqrt(x_star/xi))/np.sqrt(x_star))

def wdwSpectraFit(xi, x_star, A):
	return A*2*np.sqrt(x_star)*np.arctan(np.sqrt(x_star/xi))

### plot settings
plt.rcParams.update(plt_settings) # from library.py
color = '#1f77b4' # default matplotlib color (that blueish color)
light_color = tint_shade_color(color, amount=1+tintshade)
dark_color = tint_shade_color(color, amount=1-tintshade)
plt.rcParams.update({"figure.figsize": [12,8],
					 "font.size": 14,
					 "lines.markeredgecolor": dark_color,
					 "lines.markerfacecolor": light_color,
					 "lines.color": dark_color,
					 "lines.markeredgewidth": 2,
					 "errorbar.capsize": 0})

### loop analysis over selected datasets
for filename in files:
	
	if Analysis == False:
		break # exit loop if no analysis required, this just elims one 
			  # indentation for an if statement
	
	# run params from HFT_data.py
	print("----------------")
	print("Analyzing " + filename)
	
	df = metadata.loc[metadata.filename == filename].reset_index()
	if df.empty:
		print("Dataframe is empty! The metadata likely needs updating." )
		continue
	
	xname = df['xname'][0]
		
	ff = df['ff'][0]
	trf = df['trf'][0]  # 200 or 400 us
	gain = df['gain'][0]
	EF = df['EF'][0] #MHz
	bg_freq = df['bg_freq'][0]  # chosen freq for bg, large negative detuning
	Bfield = df['Bfield'][0]
	res_freq = df['res_freq'][0] # for 202.1G
	pulsetype = df['pulsetype'][0]
	remove_indices = df['remove_indices'][0]
	
	# create data structure
	filename = filename + ".dat"
	run = Data(filename, path=data_path)
	
	# remove indices if requested
	if remove_indices == remove_indices: # nan check
		if type(remove_indices) != int:	
			remove_list = remove_indices.strip(' ').split(',')
			remove_indices = [int(index) for index in remove_list]
		run.data.drop(remove_indices, inplace=True)
	
	num = len(run.data[xname])
	
	#### compute detuning
	run.data['detuning'] = run.data[xname] - res_freq*np.ones(num) # MHz
	
	### compute bg c5, transfer, Rabi freq, etc.
	if bg_freq == bg_freq: # nan check
		bgc5 = run.data[run.data[xname]==bg_freq]['c5'].mean()
	else: # no bg point specified, just select past Fourier width
		FourierWidth = 2/trf/1e6
		bg_cutoff = res_freq-FourierWidth
		bgc5 = run.data[run.data.detuning < bg_cutoff]['c5'].mean()
		
	run.data['N'] = run.data['c5']-bgc5*np.ones(num)+run.data['c9']*ff
	run.data['transfer'] = (run.data['c5'] - bgc5*np.ones(num))/run.data['N']
	
	# map VVA to Vpp
	if pulsetype == 'KaiserOffset' or 'BlackmanOffset':
		# split pulse into offset and amplitude
		# scale offset by VVA
		run.data['offset'] = 0.0252/VVAtoVpp(10)* \
								(run.data['vva'].apply(VVAtoVpp) )
		# calculate amplitude ignoring offset
		# gain only effects this amplitude, not the offset
		run.data['Vpp'] = gain * (run.data['vva'].apply(VVAtoVpp) 
					 - run.data['offset'])
	else:
		run.data['Vpp'] = run.data['vva'].apply(VVAtoVpp)
	
	# determine pulse area
	if pulsetype == 'Blackman':
		run.data['sqrt_pulse_area'] = np.sqrt(0.31) 
	elif pulsetype == 'Kaiser':
		run.data['sqrt_pulse_area'] = np.sqrt(0.3*0.92)
	elif pulsetype == 'square':
		run.data['sqrt_pulse_area'] = 1
	elif pulsetype == 'BlackmanOffset':
		xx = np.linspace(0,1,1000)
		# integrate the square, and sqrt it
		run.data['sqrt_pulse_area'] = np.sqrt(run.data.apply(lambda x: 
		   np.trapz((ChipBlackman(xx)*(1-x['offset']/x['Vpp']) \
			   + x['offset']/x['Vpp'])**2, x=xx), axis=1))
	elif pulsetype == 'KaiserOffset':
		xx = np.linspace(0,1,1000)
		# integrate the square, and sqrt it
		run.data['sqrt_pulse_area'] = np.sqrt(run.data.apply(lambda x: 
		   np.trapz((ChipKaiser(xx)*(1-x['offset']/x['Vpp']) \
			   + x['offset']/x['Vpp'])**2, x=xx), axis=1))
	else:
		ValueError("pulsetype not a known type")

	# compute Rabi frequency, scaled transfer, and contact
	run.data['OmegaR'] = 2*pi*run.data['sqrt_pulse_area'] \
							* VpptoOmegaR * run.data['Vpp']
	run.data['ScaledTransfer'] = run.data.apply(lambda x: GammaTilde(x['transfer'],
									h*EF*1e6, x['OmegaR']*1e3, trf), axis=1)
	run.data['C'] = run.data.apply(lambda x: 2*np.sqrt(2)*pi**2*x['ScaledTransfer'] * \
									   (np.abs(x['detuning'])/EF)**(3/2), axis=1)
	# run.data = run.data[run.data.detuning != 0]
			
	### now group by freq to get mean and stddev of mean
	run.group_by_mean(xname)
	
	### interpolate scaled transfer for sumrule integration
	xp = np.array(run.avg_data['detuning'])/EF
	fp = np.array(run.avg_data['ScaledTransfer'])
	maxfp = max(fp)
	e_maxfp = run.avg_data.iloc[run.avg_data['ScaledTransfer'].idxmax()]['em_ScaledTransfer']
	TransferInterpFunc = lambda x: np.interp(x, xp, fp)
	
	
	### ANALYSIS and PLOTTING
	fig, axs = plt.subplots(2,3)
	
	xlabel = r"Detuning $\omega_{rf}-\omega_{res}$ (MHz)"
	label = r"trf={:.0f} us, gain={:.2f}".format(trf*1e6,gain)
	
	### plot transfer fraction
	ax = axs[0,0]
	x = run.avg_data['detuning']
	y = run.avg_data['transfer']
	yerr = run.avg_data['em_transfer']
	ylabel = r"Transfer $\Gamma \,t_{rf}$"
	
	xlims = [-0.04,max(x)]
	
	ax.set(xlabel=xlabel, ylabel=ylabel, xlim=xlims)
	ax.errorbar(x, y, yerr=yerr, fmt='o')
	
	### plot scaled transfer
	ax = axs[1,0]
	x = run.avg_data['detuning']/EF
	y = run.avg_data['ScaledTransfer']
	yerr = run.avg_data['em_ScaledTransfer']
	xlabel = r"Detuning $\Delta$"
	ylabel = r"Scaled Transfer $\tilde\Gamma$"
	
	xlims = [-2,max(x)]
	axxlims = xlims
	ylims = [min(run.data['ScaledTransfer'])-0.05,
			 max(run.data['ScaledTransfer'])]
	xs = np.linspace(xlims[0], xlims[-1], len(y))
	
	ax.set(xlabel=xlabel, ylabel=ylabel, xlim=axxlims, ylim=ylims)
	ax.errorbar(x, y, yerr=yerr, fmt='o', label=label)
	ax.legend()
	
	### fit and plot -3/2 power law tail
	xlowfit = 3
	xhighfit = 8
	fitmask = x.between(xlowfit, xhighfit)
	
	x_star = xstar(Bfield)
	
	fit_func = GenerateSpectraFit(x_star)
	
	popt, pcov = curve_fit(fit_func, x[fitmask], y[fitmask], p0=[0.1], 
						sigma=yerr[fitmask])
	print('A = {:.3f} \pm {:.3f}'.format(popt[0], np.sqrt(np.diag(pcov))[0]))
	
	xmax = 1000000/EF
	xxfit = np.linspace(xlowfit, xmax, int(xmax*EF*10))
	yyfit = fit_func(xxfit, *popt)
	ax.plot(xxfit, yyfit, 'r--')
	
	### calulate integrals
	# sumrule
	SR_interp = np.trapz(TransferInterpFunc(xs), x=xs)
	SR_extrap = dwSpectraFit(xlims[-1], x_star, *popt)
	
	# first moment
	FM_interp = np.trapz(TransferInterpFunc(xs)*xs, x=xs)
	FM_extrap = wdwSpectraFit(xlims[-1], x_star, *popt)
	
	SR = SR_interp + SR_extrap
	FM = FM_interp + FM_extrap
	
	# clock shift
	CS = FM/SR
	print("raw SR {:.3f}".format(SR))
	print("raw FM {:.3f}".format(FM))
	print("raw CS {:.2f}".format(CS))
	
	### Monte-Carlo sampling for integral uncertainty
	if MonteCarlo == True:
		num_iter = 1000
		
		# sumrule, first moment and clockshift with analytic extension
		SR_MC_dist, SR_MC, e_SR_MC, FM_MC_dist, FM_MC, e_FM_MC, \
		CS_MC_dist, CS_MC, e_CS_MC, popts, pcovs \
			= MonteCarlo_spectra_fit_trapz(x, y, yerr, fitmask, x_star, 
									 fit_func)
			
		print(r"SR MC mean = {:.3f}$\pm$ {:.3f}".format(SR_MC, e_SR_MC))
		print(r"FM MC mean = {:.3f}$\pm$ {:.3f}".format(FM_MC, e_FM_MC))
		print(r"CS MC mean = {:.2f}$\pm$ {:.2f}".format(CS_MC, e_CS_MC))
	
	### plot contact
	ax = axs[0,1]
	x = run.avg_data['detuning']/EF
	y = run.avg_data['C']
	yerr = run.avg_data['em_C']
	xlabel = r"Detuning $\Delta$"
	ylabel = r"Contact $C/N$ [$k_F$]"
	
	xlims = [-2,max(x)]
	ylims = [min(run.data['C']), max(run.data['C'])]
	Cdetmin = 3
	Cdetmax = 8
	xs = np.linspace(Cdetmin, Cdetmax, num)
	
	df = run.data[run.data.detuning/EF>Cdetmin]
	Cmean = df[df.detuning/EF<Cdetmax].C.mean()
	Csem = df[df.detuning/EF<Cdetmax].C.sem()
	
	# choose sumrule for Contact normalizing as MC or raw
	if MonteCarlo:	
		C_o_SR = Cmean/(2*SR_MC)
		e_C_o_SR = C_o_SR*np.sqrt((Csem/Cmean)**2+(e_SR_MC/SR_MC)**2)
	else:
		C_o_SR = Cmean/(2*SR)
		e_C_o_SR = C_o_SR*Csem/Cmean
	
	ax.set(xlabel=xlabel, ylabel=ylabel, xlim=xlims, ylim=ylims)
	ax.errorbar(x, y, yerr=yerr, fmt='o')
	ax.plot(xs, Cmean*np.ones(num), "--")
	
	# Clock Shift from contact
	CS_pred = 1/(pi*kF*a13(Bfield)) * Cmean
	e_CS_pred = CS_pred*Csem/Cmean
	
	### plot x*Scaled transfer
	ax = axs[1,1]
	x = run.avg_data['detuning']/EF
	y = run.avg_data['ScaledTransfer'] * x
	yerr = np.abs(run.avg_data['em_ScaledTransfer'] * x)
	xlabel = r"Detuning $\Delta$"
	ylabel = r"$\Delta \tilde\Gamma$"
	
	xlims = [-2,max(x)]
	axxlims = xlims
	ylims = [min(run.data['ScaledTransfer']*run.data['detuning']/EF),
			 max(run.data['ScaledTransfer']*run.data['detuning']/EF)]
	xs = np.linspace(xlims[0], xlims[-1], len(y))
	
	ax.set(xlabel=xlabel, ylabel=ylabel, xlim=axxlims, ylim=ylims)
	ax.errorbar(x, y, yerr=yerr, fmt='o')
	xxfit = np.linspace(xlowfit, xmax, int(xmax*EF*10))
	yyfit = fit_func(xxfit, *popt)
	ax.plot(xxfit, xxfit*yyfit, 'r--')
	
	
	### generate table
	ax = axs[1,2]
	ax.axis('off')
	ax.axis('tight')
	quantities = ["Run", "SR", "FM", "CS", "Contact $C/N$","C/SR"]
	values = [filename[:-6],
			  "{:.3f}".format(SR),
			  "{:.3f}".format(FM),
			  "{:.2f}".format(CS),
			  "{:.2f}$\pm${:.2f} $k_F$".format(Cmean, Csem),
			  r"{:.2f}$\pm${:.2f}".format(C_o_SR, e_C_o_SR)
			  ]
	if MonteCarlo == True:
		quantities += ["SR MC", "FM MC", "CS MC"]
		MC_values = [r"{:.3f}$\pm${:.3f}".format(SR_MC, e_SR_MC),
				   r"{:.3f}$\pm${:.3f}".format(FM_MC, e_FM_MC),
				   r"{:.2f}$\pm${:.2f}".format(CS_MC, e_CS_MC)]
		values = values + MC_values
		
	table = list(zip(quantities, values))
	
	the_table = ax.table(cellText=table, loc='center')
	the_table.auto_set_font_size(False)
	the_table.set_fontsize(12)
	the_table.scale(1,1.5)
	
	fig.tight_layout()
	plt.show()
	
	if Saveon == True:
		datatosave = {
				   'Run':[filename], 
	 			  'Gain':[gain], 
				   'Pulse Time (us)':[trf*1e6],
				   'Pulse Type':[pulsetype],
				   'SR': [SR],
				  'FM': [FM],
				  'CS':[CS],
	 			  'C':[Cmean],
				   'e_C':[Csem],
	 			  'C/SR':[C_o_SR],
				   'e_C/SR':[e_C_o_SR],
				  'CS pred': [CS_pred],
				  'e_CS pred': [e_CS_pred],
	 			  'Peak Scaled Transfer':[maxfp], 
				  'e_Peak Scaled Transfer':[e_maxfp]}
		 
		if MonteCarlo == True:
			datatosavePlus = {
				  'SR MC': [SR_MC],
				  'e_SR MC': [e_SR_MC],
				  'FM MC': [FM_MC],
				  'e_FM MC': [e_FM_MC],
				  'CS MC': [CS_MC],
				  'e_CS MC': [e_CS_MC]}
			
			datatosave.update(datatosavePlus)
		 
		datatosavedf = pd.DataFrame(datatosave)

		### save figure
		runfolder = filename 
		figpath = os.path.join(proj_path, runfolder)
		os.makedirs(figpath, exist_ok=True)
	
		sumrulefig_name = 'Analysis_Results.png'
		sumrulefig_path = os.path.join(figpath, sumrulefig_name)
		fig.savefig(sumrulefig_path)
		 
		### save analysis results in xlsx
		try: # to open save file, if it exists
			 existing_data = pd.read_excel(savefile, sheet_name='Sheet1')
			 print("There is saved data, so adding rows to file.")
			 start_row = existing_data.shape[0] + 1
			 
			 # open file and write new results
			 with pd.ExcelWriter(savefile, mode='a', if_sheet_exists='overlay', \
					   engine='openpyxl') as writer:
				  datatosavedf.to_excel(writer, index=False, header=False, 
					   sheet_name='Sheet1', startrow=start_row)
				  
		except FileNotFoundError: # there is no save file
			 print("Save file does not exist.")
			 print("Creating file and writing header")
			 datatosavedf.to_excel(savefile, index=False, sheet_name='Sheet1')

if Summaryplots == True:
	
	### load analysis results
	df = pd.read_excel(savefile, index_col=0, engine='openpyxl').reset_index()
	
	### if MonteCarlo, select correct columns
	if MonteCarlo == True:
		SR_col = 'SR MC'
		FM_col = 'FM MC'
		CS_col = 'CS MC'
	
	else: # select non-MC columns
		SR_col = 'SR'
		FM_col = 'FM'
		CS_col = 'CS'
		df['e_SR MC'] = 0
		df['e_FM MC'] = 0
		df['e_CS MC'] = 0
		
	# get list of rf pulse times to loop over
	trflist = df['Pulse Time (us)'].unique()
	
	### plots
	fig, axes = plt.subplots(2,3)

	xlabel = r"Gain"
	
	# sumrule vs gain
	ax_SR = axes[0,0]
	ylabel = "Sumrule"
	ax_SR.set(xlabel=xlabel, ylabel=ylabel)
	
	# First Moment vs gain
	ax_FM = axes[0,1]
	ylabel = "Fist Moment"
	ax_FM.set(xlabel=xlabel, ylabel=ylabel)
		
	# Clock Shift vs gain
	ax_CS = axes[0,2]
	ylabel = "Clock Shift"
	ax_CS.set(xlabel=xlabel, ylabel=ylabel)
	
	# C vs. gain
	ax_C = axes[1,0]
	ylabel = r"Contact $C/N$ [$k_F$]"
	ax_C.set(xlabel=xlabel, ylabel=ylabel)
	
	# C/sumrule vs gain
	ax_CoSR = axes[1,1]
	ylabel = "C/sumrule"
	ax_CoSR.set(xlabel=xlabel, ylabel=ylabel)

	# peak scaled transfer vs gain
	ax_pST = axes[1,2]
	ylabel = "Peak Scaled Transfer"
	ax_pST.set(xlabel=xlabel, ylabel=ylabel)
	
	# loop over pulse times
	for i, trf in enumerate(trflist):
		sub_df = df.loc[df['Pulse Time (us)'] == trf]
		marker = markers[i]
		color = colors[i]
		
		label = r"$t_{rf}$"+"={}us".format(trf)
		
		light_color = tint_shade_color(color, amount=1+tintshade)
		dark_color = tint_shade_color(color, amount=1-tintshade)
		plt.rcParams.update({
					 "lines.markeredgecolor": dark_color,
					 "lines.markerfacecolor": light_color,
					 "lines.color": dark_color,
					 "legend.fontsize": 14})
		
		ax_C.errorbar(sub_df['Gain'], sub_df['C'], yerr=sub_df['e_C'], fmt=marker)
		ax_SR.errorbar(sub_df['Gain'], sub_df[SR_col], yerr=sub_df['e_SR MC'], fmt=marker)
		ax_CoSR.errorbar(sub_df['Gain'], sub_df['C/SR'], yerr=sub_df['e_C/SR'], fmt=marker)
		ax_pST.errorbar(sub_df['Gain'], sub_df['Peak Scaled Transfer'], 
			 yerr=sub_df['e_Peak Scaled Transfer'], fmt=marker, label=label)
		ax_FM.errorbar(sub_df['Gain'], sub_df[FM_col], yerr=sub_df['e_FM MC'], fmt=marker)
		ax_CS.errorbar(sub_df['Gain'], sub_df[CS_col], yerr=sub_df['e_CS MC'], fmt=marker)
		
	ax_pST.legend()
	fig.tight_layout()
	plt.show()

	### save figure
	timestr = time.strftime("%Y%m%d-%H%M%S")
	summary_plots_folder = "summary_plots"
	summaryfig_path = os.path.join(proj_path, summary_plots_folder)
	os.makedirs(summaryfig_path, exist_ok=True)

	summaryfig_name = timestr = time.strftime("%Y%m%d-%H%M%S")+'summary.png'
	summaryfig_path = os.path.join(summaryfig_path, summaryfig_name)
	fig.savefig(summaryfig_path)