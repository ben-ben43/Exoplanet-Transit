/**
 * Main Frontend Application Controller for ExoPlanetTransit
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentTargets = [];
    let selectedTarget = null;
    let analysisCache = {};

    // Elements
    const targetSelect = document.getElementById('target-select');
    const kicInput = document.getElementById('kic-input');
    const fetchMastBtn = document.getElementById('fetch-mast-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const windowSlider = document.getElementById('window-slider');
    const windowVal = document.getElementById('window-val');
    const minPInput = document.getElementById('min-p-input');
    const maxPInput = document.getElementById('max-p-input');
    const importanceBars = document.getElementById('importance-bars');
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-msg');

    // Initialize UI
    initTabs();
    initSliders();
    loadTargets();
    loadModelInfo();

    // Event Listeners
    targetSelect.addEventListener('change', (e) => {
        const kic = e.target.value;
        selectedTarget = currentTargets.find(t => t.kic_id === kic);
        if (selectedTarget) {
            kicInput.value = selectedTarget.kic_id;
        }
    });

    fetchMastBtn.addEventListener('click', async () => {
        const kic = kicInput.value.trim();
        if (!kic) {
            showToast('Please enter a Kepler KIC ID to fetch', 'warn');
            return;
        }

        setLoading(fetchMastBtn, true);
        try {
            const res = await fetch('/api/download_target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ kic_id: kic })
            });
            const data = await res.json();

            if (res.ok && data.status === 'success') {
                showToast(`Downloaded ${kic} from MAST archive!`, 'success');
                await loadTargets();
                targetSelect.value = data.kic_id;
                selectedTarget = currentTargets.find(t => t.kic_id === data.kic_id);
            } else {
                showToast(data.message || 'Failed downloading from MAST', 'error');
            }
        } catch (err) {
            showToast('Network error while querying MAST archive', 'error');
        } finally {
            setLoading(fetchMastBtn, false);
        }
    });

    analyzeBtn.addEventListener('click', async () => {
        const kic = kicInput.value.trim() || targetSelect.value;
        if (!kic && !selectedTarget) {
            showToast('Select a target star or enter a KIC ID first', 'warn');
            return;
        }

        const payload = {
            kic_id: kic,
            file_path: selectedTarget ? selectedTarget.file_path : null,
            window_days: parseFloat(windowSlider.value),
            min_period: parseFloat(minPInput.value) || 0.5,
            max_period: parseFloat(maxPInput.value) || 20.0
        };

        setLoading(analyzeBtn, true);
        showToast('Running autonomous detection & ML pipeline...', 'info');

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                displayAnalysisResults(data);
                showToast('Pipeline execution and ML classification complete!', 'success');
            } else {
                showToast(data.message || 'Pipeline analysis encountered an error', 'error');
            }
        } catch (err) {
            showToast('Failed connecting to server during analysis', 'error');
        } finally {
            setLoading(analyzeBtn, false);
        }
    });

    // Tab Navigation
    function initTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                const targetPane = document.getElementById(btn.dataset.tab);
                if (targetPane) {
                    targetPane.classList.add('active');
                    setTimeout(() => ChartManager.resizeAll(), 50);
                }
            });
        });

        const resetZoomBtn = document.getElementById('reset-zoom-btn');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => {
                ChartManager.resizeAll();
            });
        }
    }

    // Sliders
    function initSliders() {
        windowSlider.addEventListener('input', (e) => {
            windowVal.textContent = `${parseFloat(e.target.value).toFixed(1)} days`;
        });
    }

    // Load available targets from backend
    async function loadTargets() {
        try {
            const res = await fetch('/api/targets');
            const data = await res.json();
            if (data.status === 'success') {
                currentTargets = data.targets;
                targetSelect.innerHTML = '';

                if (currentTargets.length === 0) {
                    targetSelect.innerHTML = '<option disabled>No cached targets found</option>';
                    return;
                }

                currentTargets.forEach((t, idx) => {
                    const opt = document.createElement('option');
                    opt.value = t.kic_id;
                    const typeBadge = t.label === 1 ? '🪐 Planet' : (t.label === 0 ? '⭐ Binary' : '📁 Custom');
                    opt.textContent = `${t.name} (${typeBadge})`;
                    targetSelect.appendChild(opt);
                });

                // Auto-select first target
                selectedTarget = currentTargets[0];
                targetSelect.value = selectedTarget.kic_id;
                kicInput.value = selectedTarget.kic_id;
            }
        } catch (err) {
            console.error('Failed to load targets:', err);
        }
    }

    // Load Model Info & Feature Importance
    async function loadModelInfo() {
        try {
            const res = await fetch('/api/model_info');
            const data = await res.json();
            if (data.status === 'ready') {
                importanceBars.innerHTML = '';
                data.feature_importances.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'importance-item';
                    row.innerHTML = `
                        <div class="importance-header">
                            <span>${formatFeatureName(item.feature)}</span>
                            <span>${item.importance}%</span>
                        </div>
                        <div class="importance-bar-bg">
                            <div class="importance-bar-fill" style="width: ${item.importance}%"></div>
                        </div>
                    `;
                    importanceBars.appendChild(row);
                });
            }
        } catch (err) {
            console.error('Failed to load model info:', err);
        }
    }

    // Render Analysis Outputs
    function displayAnalysisResults(data) {
        const f = data.features;
        const ml = data.ml_verdict;
        const isPlanet = ml ? ml.prediction === 1 : (f.depth < 0.03 && f.odd_even_mismatch < 0.15);

        // 1. Verdict Banner
        const banner = document.getElementById('verdict-card');
        const vTitle = document.getElementById('verdict-title');
        const vDesc = document.getElementById('verdict-desc');
        const vIcon = document.getElementById('verdict-icon');

        banner.classList.remove('planet', 'binary');
        if (isPlanet) {
            banner.classList.add('planet');
            vIcon.textContent = '🪐';
            vTitle.textContent = 'CONFIRMED EXOPLANET CANDIDATE';
            vTitle.style.color = '#34d399';
            vDesc.textContent = `High-confidence planetary transit detected. Period P = ${data.best_period} d with consistent depth across all orbital cycles.`;
        } else {
            banner.classList.add('binary');
            vIcon.textContent = '⭐';
            vTitle.textContent = 'FALSE POSITIVE / ECLIPSING BINARY';
            vTitle.style.color = '#f59e0b';
            vDesc.textContent = `Astrophysical stellar false positive detected. Signals show secondary occultation or alternating odd-even depth disparities.`;
        }

        // 2. Probabilities & Confidence Gauge
        const gaugeCircle = document.getElementById('gauge-circle');
        const gaugeVal = document.getElementById('gauge-val');
        const planetBar = document.getElementById('prob-planet-bar');
        const planetText = document.getElementById('prob-planet-text');
        const binaryBar = document.getElementById('prob-binary-bar');
        const binaryText = document.getElementById('prob-binary-text');

        if (ml) {
            gaugeVal.textContent = `${ml.confidence}%`;
            const color = isPlanet ? '#10b981' : '#f59e0b';
            gaugeCircle.style.background = `conic-gradient(${color} ${ml.confidence}%, rgba(255,255,255,0.06) 0%)`;

            planetBar.style.width = `${ml.prob_exoplanet}%`;
            planetText.textContent = `${ml.prob_exoplanet}%`;
            binaryBar.style.width = `${ml.prob_false_positive}%`;
            binaryText.textContent = `${ml.prob_false_positive}%`;
        }

        // 3. Vetting Matrix Values
        document.getElementById('val-period').textContent = `${data.best_period} d`;
        document.getElementById('sub-epoch').textContent = `T₀ = ${data.best_t0}`;
        document.getElementById('val-depth').textContent = `${(f.depth * 100).toFixed(3)}%`;
        document.getElementById('val-snr').textContent = f.snr.toFixed(1);

        // Odd-Even Mismatch
        const oddEvenVal = (f.odd_even_mismatch * 100).toFixed(1);
        const oddEvenEl = document.getElementById('val-odd-even');
        const oddEvenBadge = document.getElementById('badge-odd-even');
        oddEvenEl.textContent = `${oddEvenVal}%`;
        if (f.odd_even_mismatch < 0.10) {
            oddEvenBadge.className = 'metric-badge badge-pass';
            oddEvenBadge.textContent = '✓ Symmetric (Planet)';
        } else {
            oddEvenBadge.className = 'metric-badge badge-fail';
            oddEvenBadge.textContent = '✗ Asymmetric (Binary)';
        }

        // Secondary Eclipse
        const secVal = (f.secondary_depth_ratio * 100).toFixed(1);
        const secEl = document.getElementById('val-secondary');
        const secBadge = document.getElementById('badge-secondary');
        secEl.textContent = `${secVal}%`;
        if (f.secondary_depth_ratio < 0.05) {
            secBadge.className = 'metric-badge badge-pass';
            secBadge.textContent = '✓ None (Planetary)';
        } else {
            secBadge.className = 'metric-badge badge-warn';
            secBadge.textContent = '⚠ Secondary Dip (Binary)';
        }

        // Flatness
        document.getElementById('val-flatness').textContent = f.transit_flatness.toFixed(2);
        document.getElementById('sub-flatness').textContent = f.transit_flatness > 1.0 ? 'Flat U-shape bottom' : 'Grazing V-shape';

        // 4. Update Orbit Simulator
        if (window.orbitSim) {
            window.orbitSim.updateParams(data.best_period, f.depth, !isPlanet);
        }

        // 5. Render All 4 Scientific Charts
        ChartManager.plotFolded('chart-folded', data.charts.folded);
        ChartManager.plotBLS('chart-bls', data.charts.bls);
        ChartManager.plotDetrended('chart-detrended', data.charts.detrended);
        ChartManager.plotRaw('chart-raw', data.charts.raw);
    }

    function formatFeatureName(name) {
        const map = {
            'depth': 'Transit Depth',
            'duration_phase': 'Duty Cycle',
            'baseline_noise': 'Baseline Noise',
            'snr': 'Signal-to-Noise',
            'secondary_depth_ratio': 'Secondary Eclipse',
            'odd_even_mismatch': 'Odd-Even Mismatch',
            'transit_flatness': 'Transit Flatness'
        };
        return map[name] || name;
    }

    function setLoading(btn, isLoading) {
        btn.disabled = isLoading;
        const spinner = btn.querySelector('.loader-spinner');
        const text = btn.querySelector('.btn-text');
        if (spinner) spinner.classList.toggle('hidden', !isLoading);
        if (text && isLoading) text.textContent = 'Processing...';
        else if (text) {
            text.textContent = btn.id === 'fetch-mast-btn' ? 'Fetch' : 'Execute Autonomous Pipeline';
        }
    }

    function showToast(message, type = 'info') {
        toastMsg.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4000);
    }
});
