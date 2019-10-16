from bokeh.plotting import figure


def make_histogram(title, hist, edges, var):
    p = figure(title=title, tools="", background_fill_color="#fafafa")
    p.quad(
        top=hist,
        bottom=0,
        left=edges[:-1],
        right=edges[1:],
        fill_color="navy",
        line_color="white",
        alpha=0.5,
    )

    p.y_range.start = 0
    p.xaxis.axis_label = f"{var}"
    p.yaxis.axis_label = f"Frequency"
    p.grid.grid_line_color = "white"
    return p


def make_categorical_hbar(
    column,
    class_index,
    title,
    plot_height=300,
    legend_1="<=50K",
    legend_2=">50K",
):
    counts_class_1 = column[class_index].value_counts()
    counts_class_2 = column[~class_index].value_counts()
    index = sorted(column.unique(), reverse=True)

    plot = figure(y_range=index, plot_height=plot_height, title=title)
    plot.hbar(
        y=counts_class_1.index,
        height=0.5,
        left=0,
        right=counts_class_1.values,
        color="navy",
        alpha=0.5,
        legend=legend_1,
    )
    plot.hbar(
        y=counts_class_2.index,
        height=0.5,
        left=0,
        right=counts_class_2.values,
        color="coral",
        alpha=0.5,
        legend=legend_2,
    )

    return plot
