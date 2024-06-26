# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 20:12:51 2024

@author: coldatoms
"""
import sys
data_class_dir = '//Users//kevinxie//Documents//GitHub//analysis'
if data_class_dir not in sys.path:
	sys.path.append(data_class_dir)
	print(sys.path)
from data_class import *
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from scipy.integrate import quad
import matplotlib.colors as mc
import colorsys

# plotting things
linewidth=5
def adjust_lightness(color, amount=0.5):
    try:
        c = mc.cnames[color]
    except:
        c = color
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0, min(1, amount * c[1])), c[2])

pi=np.pi
uatom = 1.66054e-27
mK = 39.96399848*uatom
kB =1.3806488e-23

h=6.62606957e-34
hbar = h/(2*pi)
ToTF=0.31
EF=15.2 # kHz
kF = 1.1e7

Bfield = 202.14 # G
a0 = 5.2917721092e-11 # m
re = 107 * a0
def a13(B):
	abg = 167.6*a0
	DeltaB = 7.2
	B0=224.2
	return abg*(1 - DeltaB/(B-B0))

VVAtoVppfile = data_class_dir + "//VVAtoVpp.txt" # calibration file
VVAs, Vpps = np.loadtxt(VVAtoVppfile, unpack=True)
VpptoOmegaR = 27.5833 # kHz
def VVAtoVpp(VVA):
 	"""Match VVAs to calibration file values. Will get mad if the VVA is not
		also the file. """
 	for i, VVA_val in enumerate(VVAs):
		 if VVA == VVA_val:
 			Vpp = Vpps[i]
 	return Vpp

Vpp = VVAtoVpp(1.4) -0.007
ff=1.03
trf = 640e-6
pulseArea=1
OmegaR = 2*pi*pulseArea*VpptoOmegaR*Vpp # 1/s

def dimerlineshape(omega, Eb, TMHz, fudge=0, arb_scale=1):
	# everything in MHz
	Gamma = (np.sqrt(-omega-Eb-fudge) * np.exp((omega+Eb+fudge)/TMHz)* np.heaviside(-omega - Eb-fudge, 1))* arb_scale
# 	Gamma = np.nan_to_num(Gamma)
	return Gamma

def dimerlineshape2(omega, Eb, TMHz, arb_scale=1):
	Gamma = arb_scale*(np.exp((omega - Eb)/TMHz)) / np.sqrt((-omega+Eb)) * np.heaviside(-omega+Eb, 1)
	Gamma = np.nan_to_num(Gamma)
	return Gamma

def dimerls2exp(omega, Eb, TMHz, arb_scale=1):
	Gamma = arb_scale*(np.exp((omega - Eb)/TMHz))
	return Gamma

def lineshapefit(x, A, x0, sigma):
	ls = A*np.sqrt(-x-x0) * np.exp((x + x0)/sigma) * np.heaviside(-x-x0,1)
	ls = np.nan_to_num(ls)
	return ls
# Ebfix = 3.97493557
Ebfix = -3.975*1e3 /EF
def lineshapefit_fixedEb(x, A, sigma):
	x0 = Ebfix
	ls = A*np.sqrt(-x+x0) * np.exp((x - x0)/sigma) * np.heaviside(-x+x0,1)
	ls = np.nan_to_num(ls)
	return ls

def lineshapep3fit_fixedEb(x, A, sigma):
	x0 = Ebfix
	ls = A*(-x+x0) * np.exp((x-x0)/sigma) * np.heaviside(-x+x0,1)
	ls = np.nan_to_num(ls)
	return ls

def lineshape_zeroT(x, A, x0,C):
	ls = A*(2*kF**3 - 3*kF**2*np.sqrt(-x-x0) + np.sqrt(-x-x0)**3)*np.sqrt(-x-x0)/(-x-x0) + C
	ls = np.nan_to_num(ls)
	return ls

def gaussian(x, A, x0, sigma):
	return A * np.exp(-(x-x0)**2/(2*sigma**2))



# data = Data('2023-10-02_H_e.dat', path='E:\\Data\\2023\\10 October2023\\02October2023\\H_202p1G_acdimer_1p8VVA320us', average_by='freq')
# data = Data('2023-10-02_I_e.dat', path='E:\\Data\\2023\\10 October2023\\02October2023\\I_202p1G_acdimer_1p5VVA640us', average_by='freq')
# data = Data('2024-06-12_R_e.dat', average_by='freq')
run = Data(filename='2024-06-12_S_e.dat',path = data_class_dir+'//acdimer//data')
# data = Data(filename='2024-06-20_F_e.dat',path = data_class_dir+'//acdimer//data', average_by='freq')
# data =Data('2024-06-12_T_e.dat', average_by='freq')
# field=202.1

# 20_F
# ToTF=0.33
# EF = 12 # kHz
T = ToTF * (EF*1000)
field = 202.14
freq75 = 47.2227 # MHz, 202.14 G

run.data['detuning'] = ((run.data.freq - freq75) * 1e3)/EF # kHz in units of EF
bgrange = [-3.97*1e3/EF, run.data.detuning.max()]
bgmean = np.mean(run.data[run.data['detuning'].between(bgrange[0], bgrange[1])]['sum95'])
run.data['transfer'] = (-run.data.sum95 + bgmean) / bgmean

run.data['ScaledTransfer'] = run.data.apply(lambda x: GammaTilde(x['transfer'],
								h*EF*1e3, OmegaR*1e3, trf), axis=1)
run.data['ScaledTransfer'] = run.data['ScaledTransfer'] # horrible


run.group_by_mean('detuning')


cutoff = -4.02*1e3/EF
run.avg_data['filter'] = np.where(run.avg_data['detuning'] > cutoff, 1, 0)

filtdf = run.avg_data[run.avg_data['filter']==1]
x = filtdf['detuning']
y = filtdf['ScaledTransfer']
yerr = filtdf['em_ScaledTransfer']

nfiltdf = run.avg_data[run.avg_data['filter']==0]
xnfilt = nfiltdf['detuning']
ynfilt = nfiltdf['ScaledTransfer']
yerrnfilt = nfiltdf['em_ScaledTransfer']

guess1 = [1, 4]
popt1,pcov1 = curve_fit(lineshapefit_fixedEb, x, y, sigma=yerr, p0=guess1)
perr1 = np.sqrt(np.diag(pcov1))
print('modified MB lineshape fit: ')
print(popt1)
guess2 = [1, T * 1e-3/EF]
popt2,pcov2 = curve_fit(lineshapep3fit_fixedEb, x, y, sigma=yerr, p0=guess2)
perr2 = np.sqrt(np.diag(pcov2))
print('modified MB lineshape with another relative momentum: ')
print(popt2)

guess3 = [1, -262, T * 1e-3/EF]
popt3,pcov3 = curve_fit(gaussian, x, y, sigma=yerr, p0=guess3)
perr3 = np.sqrt(np.diag(pcov3))
print('Gaussian: ')
print(popt3)


xrange=0.10*1e3/EF
xlow = Ebfix-xrange
xhigh = Ebfix + xrange
xx = np.linspace(xlow, xhigh, 100000)
yy = lineshapefit_fixedEb(xx, *popt1)
yy2 = lineshapep3fit_fixedEb(xx, *popt2)
yy3 = gaussian(xx, *popt3)
guessT0 = [4e-25,Ebfix,0]
yyT0 = lineshape_zeroT(xx, *guessT0)

fig, ax_ls = plt.subplots()
fig.suptitle('ac dimer spectrum at 202.14G, EF={:.1f} kHz, T/TF={:.2f}, T={:.1f} kHz'.format(EF, ToTF, ToTF*EF))
ax_ls.errorbar(x, y, yerr, marker='o', ls='', markersize = 12, capsize=3, mew=3, mec = adjust_lightness('tab:gray',0.2), color='tab:gray', elinewidth=3)
ax_ls.errorbar(xnfilt, ynfilt, yerrnfilt, marker='o', ls='', markersize = 12, capsize=3, mew=3, mfc='none', color='tab:gray', elinewidth=3)

fitstr = r'$A\sqrt{-\Delta-E_b}*exp(\frac{\Delta+E_b}{T}) *\Theta(-\Delta-E_b)$'
ax_ls.plot(xx, yy, ls='--', lw = linewidth, color='r', label='Mod. MB fit: ' + fitstr)
fitstr2 = r'$A (-\Delta-E_b)*exp(\frac{\Delta+E_b}{T}) *\Theta(-\Delta-E_b)$'
# ax_ls.plot(xx, yy2, ls = ':', lw = linewidth, color ='b', label = 'Mod. MB w/ collision mom.: ' + fitstr2)
# ax_ls.plot(xx, yy3, ls = '-.', lw=linewidth, color='k', label='Gaussian')
# T0str = r'$A(2k_F^3 - 3k_F^2 *\sqrt{-\omega - E_b} + \sqrt{-\omega - E_b}^3)\frac{\sqrt{-\omega-E_b}}{-\omega-E_b}$'
# ax_ls.plot(xx, yyT0, ls =':', color='g',label='T=0: ' + T0str)


textstr = '\n'.join((
 	r'Mod. MB fit params:',
 	r'Amplitude = {:.2f} +/- {:.2f}'.format(popt1[0], perr1[0]),
 	r'T = {:.2f} +/- {:.2f} EF'.format(popt1[1], perr1[1]),
	 r'Eb fixed at {:.1f} EF'.format(Ebfix)
 	))
ax_ls.text(xlow + 3, 0.018, textstr)

# arbscale=0.25e-2
arbscale = 1e-2/2
epsilon = 0.001 # small value to avoid divergence
xxZY = np.linspace(xlow, xhigh, 400)
yyZY = dimerlineshape2(xxZY, Ebfix, T/1e3/EF, arb_scale=arbscale)
# yyZY2 = dimerlineshape2(xxZY, Ebfix, 5*T/1e6, arb_scale=arbscale)
ZYstr = r'$A * exp(\frac{\Delta + E_b}{T}) * (-\Delta - E_b)^{-1/2} *\Theta(-\Delta-E_b)$'
ax_ls.plot(xxZY, yyZY, ls='-', lw=linewidth, color='g', label='Eq. (49), arb. scale, ' + ZYstr)
# ax_ls.plot(xxZY, yyZY2, ls=':', color='m', label='ZY high-T lineshape')

ax_ls.legend()
ax_ls.set_xlim([xlow, xhigh])
ax_ls.set_ylim([-0.01, 0.03])
ax_ls.set_xlim([-266, -259])
ax_ls.set_ylabel(r'Scaled transfer $\tilde{\Gamma}$ [arb.]')
ax_ls.set_xlabel(r'Detuning from 12-resonance $\Delta$ [EF]')

# how hard is it to put a second x-axis on this thing
# Put MHz frequencies on upper x-axis
f = lambda x: x * EF /1e3 
g = lambda x: x * EF/1e3 #wtf
ax2 = ax_ls.secondary_xaxis("top", functions=(f,g))
ax2.set_xlabel("Detuning [MHz]")


plt.tight_layout()

fig.savefig('figures/acdimerspectrum_fit.pdf')


### time for clock shift analysis I guess

sumrule1 = np.trapz(lineshapefit_fixedEb(xx, *popt1), x=xx)
sumrule2 = np.trapz(lineshapep3fit_fixedEb(xx, *popt2), x=xx)
sumrule3 = np.trapz(gaussian(xx, *popt3), x=xx)
print("sumrule1 = {:.6f}".format(sumrule1))
print("sumrule2 = {:.6f}".format(sumrule2))
print("sumrule3 = {:.6f}".format(sumrule3))

firstmoment1 = np.trapz(lineshapefit_fixedEb(xx, *popt1) * xx, x=xx)
firstmoment2 = np.trapz(lineshapep3fit_fixedEb(xx, *popt2) * xx, x=xx)
firstmoment3 = np.trapz(gaussian(xx, *popt3) * xx, x=xx)
print("first moment1 [EF] = {:.6f}".format(firstmoment1))
print("first moment2 [EF] = {:.6f}".format(firstmoment2))
print("first moment3 [EF] = {:.6f}".format(firstmoment3))

# clock shifts
# HFTsumrule = 0.43*2 
HFTsumrule = 0.96 # fudged to make the whole thing 1
clockshift1 = firstmoment1/(sumrule1+HFTsumrule)
clockshift2 = firstmoment2/(sumrule2+HFTsumrule)
clockshift3 = firstmoment3/(sumrule3+HFTsumrule)
print("Clock shift1 [EF]= {:.6f}".format(clockshift1))
print("Clock shift2 [EF] = {:.6f}".format(clockshift2))
print("Clock shift3 [EF] = {:.6f}".format(clockshift3))

Ctilde_est = 1.44
cs_pred = -2/(pi*kF*a13(Bfield))*Ctilde_est
print("predicted dimer clock shift [Eq. (5)]: "+ str(cs_pred))

cstot_pred_zerorange = -1/(pi*kF*a13(Bfield)) * Ctilde_est
print("Predicted total clock shift w/o eff. range term [Eq. (1)]: "+ str(cstot_pred_zerorange))
csHFT_pred = cstot_pred_zerorange-cs_pred
print("Predicted HFT clock shift w/o eff. range term: " + str(csHFT_pred))

cstot_pred = -1/(pi*kF*a13(Bfield)) * (1- pi**2/8*re/a13(Bfield)) * Ctilde_est
print("Predicted total clock shift w/ eff. range term [Eq. (1)]: "+ str(cstot_pred))
csHFT_pred = cstot_pred-cs_pred
print("Predicted HFT clock shift w/ eff. range term: " + str(csHFT_pred))
kappa = 1.2594*1e8
I_d = kF*Ctilde_est / (pi * kappa) * (1/1+re/a13(Bfield))
print("Predicted dimer spectral weight [Eq. 6]: " + str(I_d))




### generate table
fig, ax = plt.subplots()
ax.axis('off')
ax.axis('tight')
# quantities = ["sumrule (red)", "1st moment (red)", "Clock shift (red)", \
# 			  "sumrule (blue)", "1st moment (blue)", "Clock shift (blue)", \
# 				  "sumrule (black)", "1st moment (black)", "Clock shift (black)"]
# values = ["{:.3f}".format(sumrule1),
# 		  "{:.3f}".format(firstmoment1),
# 		  "{:.3f}".format(clockshift1), 
# 		  "{:.3f}".format(sumrule2),
# 		  "{:.3f}".format(firstmoment2),
# 		  "{:.3f}".format(clockshift2),
# 		  "{:.3f}".format(sumrule3),
# 		  "{:.3f}".format(firstmoment3),
# 		  "{:.3f}".format(clockshift3)]
quantities = [r"$\Omega_d$ (red)", \
			     r"$\Omega_d$ (blue)", \
				  r"$\Omega_d$ (black)", \
					  r"$\Omega_+$ (zero range)", \
						  r"$\Omega_+$", \
						  r"$\Omega_{tot}$ (zero range)", \
							r"$\Omega_{tot}$"  ]
HFT_CS_zerorange = 5.4
HFT_CS = 7.4
values = ["{:.3f}".format(clockshift1), 
		  "{:.3f}".format(clockshift2),
		  "{:.3f}".format(clockshift3),
		  "{:.3f}".format(HFT_CS_zerorange),
		  "{:.3f}".format(HFT_CS),
		  "{:.3f}".format(cstot_pred_zerorange),\
			  "{:.3f}".format(cstot_pred)]
table = list(zip(quantities, values))

the_table = ax.table(cellText=table, loc='center')
the_table.auto_set_font_size(False)
the_table.set_fontsize(12)
the_table.scale(1,1.5)
