// Dashboard initialization and utility functions
document.addEventListener('DOMContentLoaded', function() {
    // Configure default Plotly layout options
    const defaultLayout = {
        autosize: true,
        margin: { t: 20, b: 40, l: 40, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            family: 'Arial, sans-serif'
        }
    };

    // Configure default Plotly config
    const defaultConfig = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: [
            'lasso2d',
            'select2d',
            'toggleSpikelines'
        ]
    };

    // Apply these defaults to all plots
    const plots = document.querySelectorAll('[id$="Chart"]');
    plots.forEach(plot => {
        if (plot._Plotly) {
            Plotly.relayout(plot.id, defaultLayout);
        }
    });
}); 