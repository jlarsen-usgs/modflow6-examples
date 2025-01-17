# ## Flowing well Multi-Aquifer Well Problem,
#
# This is a modified version of the Neville-Tonkin Multi-Aquifer Well problem
# from Neville and Tonkin, 2004 that uses the flowing well option.
#

# ### Flowing Well Problem Setup
#
# Imports

import os
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import flopy

# Append to system path to include the common subdirectory

sys.path.append(os.path.join("..", "common"))

# import common functionality

import config
from figspecs import USGSFigure

# Set figure properties specific to the

figure_size = (6.3, 4.3)
masked_values = (0, 1e30, -1e30)

# Base simulation and model name and workspace

ws = config.base_ws

# Simulation name

sim_name = "ex-gwf-maw-p02"

# Model units

length_units = "meters"
time_units = "days"

# Table Flowing Well Problem Model Parameters

nper = 1  # Number of periods
nlay = 2  # Number of layers
nrow = 101  # Number of rows
ncol = 101  # Number of columns
delr = 142.0  # Column width ($m$)
delc = 142.0  # Row width ($m$)
top = -50.0  # Top of the model ($m$)
botm_str = "-142.9, -514.5"  # Bottom elevations ($m$)
strt_str = "3.05, 9.14"  # Starting head ($m$)
k11 = 1.0  # Horizontal hydraulic conductivity ($m/d$)
k33 = 1.0e-16  # Vertical hydraulic conductivity ($m/d$)
ss = 1e-4  # Specific storage ($1/d$)
maw_radius = 0.15  # Well radius ($m$)
maw_rate = 0.0  # Well pumping rate ($m^{3}/d$)

# parse parameter strings into tuples

botm = [float(value) for value in botm_str.split(",")]
strt = [float(value) for value in strt_str.split(",")]

# Static temporal data used by TDIS file

tdis_ds = ((2.314815, 50, 1.2),)

# Define dimensions

extents = (0.0, delr * ncol, 0.0, delc * nrow)
shape2d = (nrow, ncol)
shape3d = (nlay, nrow, ncol)

# create idomain

idomain = np.ones(shape3d, dtype=float)
xw, yw = (ncol / 2) * delr, (nrow / 2) * delc
y = 0.0
for i in range(nrow):
    x = 0.0
    y = (float(i) + 0.5) * delc
    for j in range(ncol):
        x = (float(j) + 0.5) * delr
        r = np.sqrt((x - xw) ** 2.0 + (y - yw) ** 2.0)
        if r > 7163.0:
            idomain[:, i, j] = 0

# ### Create Flowing Well Problem Model Boundary Conditions

# MAW Package

maw_row = int(nrow / 2)
maw_col = int(ncol / 2)

maw_packagedata = [[0, maw_radius, botm[-1], strt[-1], "SPECIFIED", 2]]

maw_conn = [
    [0, 0, 0, maw_row, maw_col, top, botm[-1], 111.3763, -999.0],
    [0, 1, 1, maw_row, maw_col, top, botm[-1], 445.9849, -999.0],
]

maw_spd = [[0, "rate", maw_rate], [0, "flowing_well", 0.0, 7500.0, 0.5]]

# Solver parameters

nouter = 500
ninner = 100
hclose = 1e-9
rclose = 1e-4


# ### Functions to build, write, run, and plot the MODFLOW 6 Flowing Well Problem model
#
# MODFLOW 6 flopy simulation object (sim) is returned if building the model


def build_model():
    if config.buildModel:
        sim_ws = os.path.join(ws, sim_name)
        sim = flopy.mf6.MFSimulation(
            sim_name=sim_name, sim_ws=sim_ws, exe_name=config.mf6_exe
        )
        flopy.mf6.ModflowTdis(
            sim, nper=nper, perioddata=tdis_ds, time_units=time_units
        )
        flopy.mf6.ModflowIms(
            sim,
            print_option="summary",
            outer_maximum=nouter,
            outer_dvclose=hclose,
            inner_maximum=ninner,
            inner_dvclose=hclose,
            rcloserecord="{} strict".format(rclose),
        )
        gwf = flopy.mf6.ModflowGwf(sim, modelname=sim_name, save_flows=True)
        flopy.mf6.ModflowGwfdis(
            gwf,
            length_units=length_units,
            nlay=nlay,
            nrow=nrow,
            ncol=ncol,
            delr=delr,
            delc=delc,
            top=top,
            botm=botm,
            idomain=idomain,
        )
        flopy.mf6.ModflowGwfnpf(
            gwf,
            icelltype=0,
            k=k11,
            k33=k33,
            save_specific_discharge=True,
        )
        flopy.mf6.ModflowGwfsto(
            gwf,
            iconvert=0,
            ss=ss,
        )
        flopy.mf6.ModflowGwfic(gwf, strt=strt)

        maw = flopy.mf6.ModflowGwfmaw(
            gwf,
            flowing_wells=True,
            nmawwells=1,
            packagedata=maw_packagedata,
            connectiondata=maw_conn,
            perioddata=maw_spd,
        )
        obs_file = "{}.maw.obs".format(sim_name)
        csv_file = obs_file + ".csv"
        obs_dict = {
            csv_file: [
                ("head", "head", (0,)),
                ("Q1", "maw", (0,), (0,)),
                ("Q2", "maw", (0,), (1,)),
                ("FW", "fw-rate", (0,)),
            ]
        }
        maw.obs.initialize(
            filename=obs_file, digits=10, print_input=True, continuous=obs_dict
        )

        flopy.mf6.ModflowGwfoc(
            gwf,
            printrecord=[("BUDGET", "LAST")],
        )
        return sim
    return None


# Function to write MODFLOW 6 Flowing Well Problem model files


def write_model(sim, silent=True):
    if config.writeModel:
        sim.write_simulation(silent=silent)


# Function to run the Flowing Well Problem model.
# True is returned if the model runs successfully
#


@config.timeit
def run_model(sim, silent=True):
    success = True
    if config.runModel:
        success, buff = sim.run_simulation(silent=silent)
        if not success:
            print(buff)
    return success


# Function to plot the lake results


def plot_maw_results(silent=True):
    fs = USGSFigure(figure_type="graph", verbose=False)

    # load the observations
    fpth = os.path.join(ws, sim_name, "{}.maw.obs.csv".format(sim_name))
    maw = flopy.utils.Mf6Obs(fpth).data

    time = maw["totim"] * 86400.0

    tmin = time[0]
    tmax = time[-1]

    # create the figure
    fig, axes = plt.subplots(
        ncols=1,
        nrows=2,
        sharex=True,
        figsize=figure_size,
        constrained_layout=True,
    )

    ax = axes[0]
    ax.set_xlim(tmin, tmax)
    ax.set_ylim(0, 4500)
    ax.semilogx(
        time,
        maw["Q1"],
        lw=0.75,
        ls="-",
        color="blue",
        label="Upper aquifer",
    )
    ax.semilogx(
        time,
        maw["Q2"],
        lw=0.75,
        ls="-",
        color="red",
        label="Lower aquifer",
    )
    ax.axhline(0, lw=0.5, color="0.5")
    ax.set_ylabel(" ")
    fs.heading(ax, idx=0)
    # fs.graph_legend(ax, loc="upper right", ncol=2)

    ax = axes[1]
    ax.set_xlim(tmin, tmax)
    ax.set_ylim(-4500, 0)
    ax.axhline(
        10.0,
        lw=0.75,
        ls="-",
        color="blue",
        label="Upper aquifer",
    )
    ax.axhline(
        10.0,
        lw=0.75,
        ls="-",
        color="red",
        label="Lower aquifer",
    )
    ax.semilogx(
        time,
        maw["FW"],
        lw=0.75,
        ls="-",
        color="black",
        label="Flowing well discharge",
    )
    ax.set_xlabel(" ")
    ax.set_ylabel(" ")
    for axis in (ax.xaxis,):
        axis.set_major_formatter(mpl.ticker.ScalarFormatter())
    fs.heading(ax, idx=1)
    fs.graph_legend(ax, loc="upper left", ncol=1)

    # add y-axis label that spans both subplots
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # get rid of ticks and spines for legend area
    # ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["top"].set_color("none")
    ax.spines["bottom"].set_color("none")
    ax.spines["left"].set_color("none")
    ax.spines["right"].set_color("none")
    ax.patch.set_alpha(0.0)

    ax.set_xlabel("Simulation time, in seconds")
    ax.set_ylabel("Discharge rate, in cubic meters per day")

    # save figure
    if config.plotSave:
        fpth = os.path.join(
            "..",
            "figures",
            "{}-01{}".format(sim_name, config.figure_ext),
        )
        fig.savefig(fpth)

    return


# Plot the grid


def plot_grid(sim, silent=True):
    gwf = sim.get_model(sim_name)
    fs = USGSFigure(figure_type="map", verbose=False)
    fig = plt.figure(
        figsize=(4, 4.3),
        tight_layout=True,
    )
    plt.axis("off")

    nrows, ncols = 10, 1
    axes = [fig.add_subplot(nrows, ncols, (1, 8))]

    for idx, ax in enumerate(axes):
        ax.set_xlim(extents[:2])
        ax.set_ylim(extents[2:])
        ax.set_aspect("equal")

    # legend axis
    axes.append(fig.add_subplot(nrows, ncols, (9, 10)))

    # set limits for legend area
    ax = axes[-1]
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # get rid of ticks and spines for legend area
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["top"].set_color("none")
    ax.spines["bottom"].set_color("none")
    ax.spines["left"].set_color("none")
    ax.spines["right"].set_color("none")
    ax.patch.set_alpha(0.0)

    ax = axes[0]
    mm = flopy.plot.PlotMapView(gwf, ax=ax, extent=extents)
    mm.plot_bc("MAW", color="red")
    mm.plot_inactive(color_noflow="black")
    ax.set_xticks([0, extents[1] / 2, extents[1]])
    ax.set_yticks([0, extents[1] / 2, extents[1]])

    ax = axes[-1]
    ax.plot(
        -10000,
        -10000,
        lw=0,
        marker="s",
        ms=10,
        mfc="black",
        mec="black",
        markeredgewidth=0.5,
        label="Inactive cells",
    )
    ax.plot(
        -10000,
        -10000,
        lw=0,
        marker="s",
        ms=10,
        mfc="red",
        mec="red",
        markeredgewidth=0.5,
        label="Multi-aquifer well",
    )
    fs.graph_legend(ax, loc="lower center", ncol=2)

    # save figure
    if config.plotSave:
        fpth = os.path.join(
            "..",
            "figures",
            "{}-grid{}".format(sim_name, config.figure_ext),
        )
        fig.savefig(fpth)


# Function to plot the Flowing Well Problem model results.


def plot_results(sim, silent=True):
    if config.plotModel:
        plot_grid(sim, silent=silent)
        plot_maw_results(silent=silent)


# Function that wraps all of the steps for the Flowing Well Problem model
#
# 1. build_model,
# 2. write_model,
# 3. run_model, and
# 4. plot_results.
#


def simulation(silent=True):
    sim = build_model()

    write_model(sim, silent=silent)

    success = run_model(sim, silent=silent)
    assert success, "could not run...{}".format(sim_name)

    if success:
        plot_results(sim, silent=silent)


# nosetest - exclude block from this nosetest to the next nosetest
def test_01():
    simulation(silent=False)


# nosetest end

if __name__ == "__main__":
    # ### Flowing Well Problem Simulation

    simulation()
