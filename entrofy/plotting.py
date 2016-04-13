import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import seaborn as sns

from entrofy.mappers import ObjectMapper, ContinuousMapper


__all__ = ["plot", "plot_fractions", "plot_correlation", "plot_distribution"]

def _make_counts_summary(column, key, mapper, datatype="all"):
    """
    Summarize the statistics of the input column.

    Parameters
    ----------
    column : pd.Series object
        A series object with the relevant data

    key : string
        The name of the data column. Used for plotting.

    mapper : mapper.BaseMapper subclass instance
        The mapper object that defines how the data in `column` are binarized.

    datatype : string
        Flag used to distinguish between DataFrames returned by this function.


    Returns
    -------
    summary : pd.DataFrame
        A data frame with columns [key, "counts", "type"] describing the
        different categorical entries in the (binarized) column, the fraction
        of rows in `column` with that entry and the data type defined in the
        keyword `datatype`.

    TODO: This should probably take opt-outs into account?

    """
    binary = mapper.transform(column)
    describe = binary.describe()

    summary_data = np.array([describe.columns.values, describe.loc["mean"]]).T
    summary = pd.DataFrame(summary_data, columns=[key, "counts"])
    summary["type"] = [datatype for _ in range(len(summary.index))]

    return summary

def plot_fractions(column, idx, key, mapper):
    """
    Plot the fractions

    Parameters
    ----------
    column : pd.Series
        A pandas Series object with the data.

    idx : iterable
        An iterable containing the indices of selected participants.

    key : string
        Column name (used for plotting)

    mapper : entrofy.BaseMapper subclass instance
        Dictionary mapping dataframe columns to BaseMapper objects


    Returns
    -------
    fig : matplotlib.Figure object
        The Figure object with the plot

    summary : pd.DataFrame
        A pandas DataFrame containing the summary statistics
    """

    # compute the summary of the full data set
    full_summary = _make_counts_summary(column, key, mapper, datatype="all")

    # compute the summary of the selected participants
    selected_summary = _make_counts_summary(column[idx], key, mapper,
                                            datatype="selected")

    # concatenate the two DataFrames
    summary = pd.concat([full_summary, selected_summary])

    # sort data frames by relevant keyword in alphabetical order
    summary = summary.sort(key)

    # find all unique labels
    unique_labels = len(full_summary.index)

    # make figure
    fig, ax = plt.subplots(1,1, figsize=(4*unique_labels, 8))
    sns.barplot(x=key, y="counts", hue="type", data=summary, ax=ax)
    ax.set_ylabel("Fraction of sample")

    # add targets
    for i,l in enumerate(np.sort(mapper.targets.keys())):
        ax.hlines(mapper.targets[l], -0.5+i*1.0, 0.5+i*1.0, lw=2,
                  linestyle="dashed")

    return fig, summary

def plot(df, idx, mappers):
    """
    Plot bar plots for all columns in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        A pandas DataFrame object with the data.

    idx : iterable
        An iterable containing the indices of selected participants.

    mappers :  dict {column: entrofy.BaseMapper}
        Dictionary mapping dataframe columns to BaseMapper objects

    Returns
    -------
    fig_all : list of matplotlib.Figure objects
        The list containing all Figure objects with the plots.

    """

    columns = mappers.keys()

    fig_all = []
    for c in columns:
        fig, _ = plot_fractions(df[c], idx, c, mappers[c])
        fig_all.append(fig)

    return fig_all



def _plot_categorical(df, xlabel, ylabel, x_fields, y_fields,
                      x_keys, y_keys, prefac, ax, cmap):

    tuples, counts = [], []
    for i in range(x_fields):
        for j in range(y_fields):
            tuples.append((i,j))
            counts.append(len(df[(df[xlabel] == x_keys[i]) &
                                 (df[ylabel] == y_keys[j])]))

    x, y = zip(*tuples)

    cmap = plt.cm.get_cmap(cmap)
    sizes = np.array(counts)**2.0

    ax.scatter(x, y, s=sizes, marker='o', linewidths=1, edgecolor='black',
                c=cmap(prefac*sizes/(np.max(sizes)-np.min(sizes))), alpha=0.7)

    ax.set_xticks(np.arange(len(x_keys)))
    ax.set_xticklabels(x_keys)
    ax.set_xlim(np.min(x)-1, np.max(x)+1)
    ax.set_xlabel(xlabel)

    ax.set_yticks(np.arange(len(y_keys)))
    ax.set_yticklabels(y_keys)
    ax.set_ylim(np.min(y)-1, np.max(y)+1)
    ax.set_ylabel(ylabel)

    return ax

def _convert_continuous_to_categorical(column, mapper):
    binary = mapper.transform(column)
    b_stacked = binary.stack()
    cat_column = pd.Series(pd.Categorical(b_stacked[b_stacked != 0].index.get_level_values(1)))
    return cat_column

def _plot_categorical_and_continuous(df, xlabel, ylabel, ax, cmap,
                                     n_cat=5, plottype="box"):

    current_palette = sns.color_palette(cmap, n_cat)
    if plottype == "box":
        sns.boxplot(x=xlabel, y=ylabel, data=df,
                    palette=current_palette, ax=ax)
    elif plottype == "strip":
        sns.stripplot(x=xlabel, y=ylabel, data=df,
                      palette=current_palette, ax=ax)
    elif plottype == "swarm":
        sns.swarmplot(x=xlabel, y=ylabel, data=df,
                      palette=current_palette, ax=ax)
    elif plottype == "violin":
        sns.violinplot(x=xlabel, y=ylabel, data=df,
                       palette=current_palette, ax=ax)
    return ax


def _plot_continuous(df, xlabel, ylabel, ax, plottype="kde", n_levels=10,
                     cmap="YlGnBu", shade=True):
    xcolumn = df[xlabel]
    ycolumn = df[ylabel]
    x_clean = xcolumn[np.isfinite(xcolumn) & np.isfinite(ycolumn)]
    y_clean = ycolumn[np.isfinite(ycolumn) & np.isfinite(xcolumn)]

    if plottype == "kde":
        sns.kdeplot(x_clean, y_clean, n_levels=n_levels, shade=shade,
                    ax=ax, cmap=cmap)

    elif plottype == "scatter":
        current_palette = sns.color_palette(cmap, 5)
        c = current_palette[2]
        ax.scatter(x_clean, y_clean, color=c, s=10, lw=0,
                   edgecolor="none", alpha=0.8)

    return ax

def plot_correlation(df, xlabel, ylabel, xmapper=None, ymapper=None,
                      ax = None, xtype="categorical", ytype="categorical",
                      cmap="YlGnBu", prefac=10., cat_type="box", n_out=3,
                      cont_type="kde"):

    if ax is None:
        fig, ax = plt.subplots(1,1, figsize=(9,7))

    if xtype == "categorical":
        if xmapper is None:
            xmapper = ObjectMapper(df[xlabel])

        x_fields = len(xmapper.targets)
        x_keys = np.sort(xmapper.targets.keys())
    elif xtype == "continuous":
        if xmapper is None:
            xmapper = ContinuousMapper(df[xlabel], n_out=n_out)
        x_fields = None
        x_keys = xlabel
    else:
        raise Exception("Type of data in xcolumn is not recognized!")

    if ytype == "categorical":
        if ymapper is None:
            ymapper = ObjectMapper(df[ylabel])
        y_fields = len(ymapper.targets)
        y_keys = np.sort(ymapper.targets.keys())
    elif ytype == "continuous":
        if ymapper is None:
            ymapper = ContinuousMapper(df[ylabel], n_out=n_out)
        y_fields = None
        y_keys = ylabel

    if (xtype == "categorical") & (ytype == "categorical"):
        ax = _plot_categorical(df, xlabel, ylabel,
                               x_fields, y_fields,
                               x_keys, y_keys, prefac,
                               ax, cmap)

    elif ((xtype == "categorical") & (ytype == "continuous")):
        n_cat = x_fields
        if cat_type == "categorical":
            cat_column = _convert_continuous_to_categorical(df[ylabel],
                                                            ymapper)
            cat_column.name = ylabel
            y_fields = len(ymapper.targets)
            y_keys = np.sort(ymapper.targets.keys())
            df_temp = pd.DataFrame([df[xlabel], cat_column]).transpose()

            ax = _plot_categorical(df_temp, xlabel, ylabel,
                                   x_fields, y_fields,
                                   x_keys, y_keys, prefac,
                                   ax, cmap)
        else:
            ax = _plot_categorical_and_continuous(df, xlabel, ylabel,
                                                  ax, cmap, n_cat=n_cat,
                                                  plottype=cat_type)

    elif ((xtype == "continuous") & (ytype == "categorical")):
        n_cat = y_fields

        if cat_type == "categorical":
            cat_column = _convert_continuous_to_categorical(df[xlabel],
                                                            xmapper)
            x_fields = len(xmapper.targets)
            x_keys = np.sort(xmapper.targets.keys())

            df_temp = pd.DataFrame([cat_column, df[ylabel]],
                                   columns=[xlabel, ylabel])

            ax = _plot_categorical(df_temp, xlabel, ylabel,
                               x_fields, y_fields,
                               x_keys, y_keys, prefac,
                               ax, cmap)

        else:
            ax = _plot_categorical_and_continuous(df, xlabel, ylabel,
                                                  ax, cmap, n_cat=n_cat,
                                                  plottype=cat_type)

    elif ((xtype == "continuous") & (ytype == "continuous")):
        ax = _plot_continuous(df, xlabel, ylabel, ax, plottype=cont_type,
                              n_levels=10, cmap="YlGnBu", shade=True)

    else:
        raise Exception("Not currently supported!")

    return ax

def plot_distribution(df, xlabel, xmapper=None, xtype="categorical", ax=None,
              cmap="YlGnBu", nbins=30):

    if xmapper is None:
        if xtype == "categorical":
            xmapper = ObjectMapper(df[xlabel])
        elif xtype == "continuous":
            xmapper = ContinuousMapper(df[xlabel])
        else:
            raise Exception("xtype not valid.")

    c = sns.color_palette(cmap, 5)[2]

    if ax is None:
        fig, ax = plt.subplots(1,1, figsize=(8,6))
    if xtype == "categorical":
        summary = _make_counts_summary(df[xlabel], xlabel,
                                       xmapper, datatype="all")

        summary = summary.sort(xlabel)

        #make figure
        sns.barplot(x=xlabel, y="counts", data=summary, ax=ax, color=c)
        ax.set_ylabel("Fraction of sample")

    elif xtype == "continuous":
        column = df[xlabel]
        c_clean = column[np.isfinite(column)]
        _, _, _ = ax.hist(c_clean, bins=nbins, histtype="stepfilled",
                                 alpha=0.8, color=c)
        ax.set_xlabel(xlabel)
        plt.ylabel("Number of occurrences")

    return c