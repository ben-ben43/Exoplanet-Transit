/**
 * Scientific Charting Module for ExoPlanetTransit using Plotly.js
 */

const ChartManager = {
    theme: {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(13, 17, 26, 0.6)',
        font: {
            family: 'Outfit, sans-serif',
            color: '#94a3b8',
            size: 11
        },
        gridcolor: 'rgba(255, 255, 255, 0.05)',
        zerolinecolor: 'rgba(255, 255, 255, 0.1)'
    },

    commonLayout: function(title, xaxisTitle, yaxisTitle) {
        return {
            paper_bgcolor: this.theme.paper_bgcolor,
            plot_bgcolor: this.theme.plot_bgcolor,
            font: this.theme.font,
            margin: { t: 40, r: 25, b: 45, l: 60 },
            title: {
                text: title,
                font: { size: 14, color: '#f8fafc', weight: 700 },
                x: 0.02,
                xanchor: 'left'
            },
            xaxis: {
                title: { text: xaxisTitle, font: { size: 12, color: '#94a3b8' } },
                gridcolor: this.theme.gridcolor,
                zerolinecolor: this.theme.zerolinecolor,
                color: '#94a3b8'
            },
            yaxis: {
                title: { text: yaxisTitle, font: { size: 12, color: '#94a3b8' } },
                gridcolor: this.theme.gridcolor,
                zerolinecolor: this.theme.zerolinecolor,
                color: '#94a3b8'
            },
            hoverlabel: {
                bgcolor: '#1e293b',
                bordercolor: '#38bdf8',
                font: { color: '#ffffff', family: 'Space Grotesk, monospace' }
            },
            autosize: true
        };
    },

    plotRaw: function(containerId, rawData) {
        const trace = {
            x: rawData.time,
            y: rawData.flux,
            mode: 'markers',
            type: 'scattergl',
            marker: {
                size: 3.5,
                color: '#64748b',
                opacity: 0.85
            },
            name: 'Kepler Flux (e⁻/s)'
        };

        const layout = this.commonLayout(
            'Phase 1: Raw Quality-Filtered Kepler Telemetry',
            'Time (BJD - 2454833)',
            'Instrument Flux (e⁻/s)'
        );

        const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] };
        Plotly.newPlot(containerId, [trace], layout, config);
    },

    plotDetrended: function(containerId, detrendedData) {
        const fluxTrace = {
            x: detrendedData.time,
            y: detrendedData.flux,
            mode: 'markers',
            type: 'scattergl',
            marker: {
                size: 3.5,
                color: '#38bdf8',
                opacity: 0.8
            },
            name: 'Detrended Flux'
        };

        const baselineTrace = {
            x: [Math.min(...detrendedData.time), Math.max(...detrendedData.time)],
            y: [1.0, 1.0],
            mode: 'lines',
            line: { color: '#f43f5e', dash: 'dash', width: 1.5 },
            name: 'Normalized Baseline (1.0)'
        };

        const layout = this.commonLayout(
            'Phase 2: Stellar Baseline Detrended & Flattened Light Curve',
            'Time (BJD - 2454833)',
            'Relative Normalized Flux'
        );

        const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] };
        Plotly.newPlot(containerId, [fluxTrace, baselineTrace], layout, config);
    },

    plotBLS: function(containerId, blsData) {
        const spectrumTrace = {
            x: blsData.periods,
            y: blsData.powers,
            mode: 'lines',
            line: {
                color: '#818cf8',
                width: 1.8
            },
            name: 'BLS Power (SNR)'
        };

        const peakTrace = {
            x: [blsData.peak_period],
            y: [blsData.peak_power],
            mode: 'markers+text',
            type: 'scatter',
            marker: { size: 12, color: '#f59e0b', symbol: 'star' },
            text: [`P = ${blsData.peak_period.toFixed(4)} d`],
            textposition: 'top center',
            textfont: { color: '#f59e0b', family: 'Space Grotesk, monospace', size: 12 },
            name: 'Optimal Peak'
        };

        const layout = this.commonLayout(
            'Phase 3: Box-Fitting Least Squares (BLS) Periodogram Spectrum',
            'Trial Orbital Period (Days)',
            'BLS Detection Power (SNR)'
        );

        const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] };
        Plotly.newPlot(containerId, [spectrumTrace, peakTrace], layout, config);
    },

    plotFolded: function(containerId, foldedData) {
        const scatterTrace = {
            x: foldedData.phase,
            y: foldedData.flux,
            mode: 'markers',
            type: 'scattergl',
            marker: {
                size: 5,
                color: '#f43f5e',
                opacity: 0.75
            },
            name: 'Folded Cadences'
        };

        const baselineTrace = {
            x: [-0.3, 0.3],
            y: [1.0, 1.0],
            mode: 'lines',
            line: { color: '#38bdf8', dash: 'dash', width: 1.2 },
            name: 'Stellar Continuum'
        };

        const layout = this.commonLayout(
            'Phase 4: Autonomous Phase-Folded Transit Profile',
            'Orbital Phase (Transit Center = 0.0)',
            'Relative Normalized Flux'
        );
        layout.xaxis.range = [-0.22, 0.22];

        const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] };
        Plotly.newPlot(containerId, [scatterTrace, baselineTrace], layout, config);
    },

    resizeAll: function() {
        ['chart-raw', 'chart-detrended', 'chart-bls', 'chart-folded'].forEach(id => {
            const el = document.getElementById(id);
            if (el && el.data) {
                Plotly.Plots.resize(el);
            }
        });
    }
};

window.ChartManager = ChartManager;
