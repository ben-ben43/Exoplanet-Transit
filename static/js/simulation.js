/**
 * Cosmic Orbit Transit Simulator
 * Renders an animated Keplerian star-planet/binary system on HTML5 Canvas.
 */

class OrbitSimulation {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.isRunning = true;
        this.phase = 0.0;
        this.speed = 0.003; // phase per frame
        this.period = 2.48; // default in days
        this.transitDepth = 0.01;
        this.isBinary = false;
        
        // Visual constants
        this.starRadius = 38;
        this.orbitRadiusX = 170;
        this.orbitRadiusY = 32;
        this.tiltAngle = 12 * Math.PI / 180;
        
        this.initControls();
        this.resize();
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }
    
    initControls() {
        const playBtn = document.getElementById('sim-play-btn');
        const resetBtn = document.getElementById('sim-reset-btn');
        
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                this.isRunning = !this.isRunning;
                playBtn.textContent = this.isRunning ? '⏸️ Pause' : '▶️ Resume';
            });
        }
        
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.phase = 0.0;
            });
        }
        
        window.addEventListener('resize', () => this.resize());
    }
    
    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }
    
    updateParams(period, depth, isBinary = false) {
        this.period = period || 2.48;
        this.transitDepth = depth || 0.01;
        this.isBinary = isBinary;
    }
    
    animate() {
        if (this.isRunning) {
            this.phase += this.speed;
            if (this.phase > 0.5) this.phase -= 1.0;
        }
        
        this.draw();
        this.updateUI();
        requestAnimationFrame(this.animate);
    }
    
    updateUI() {
        const phaseVal = document.getElementById('sim-phase-val');
        const statusPill = document.getElementById('sim-status-pill');
        
        if (phaseVal) {
            phaseVal.textContent = (this.phase >= 0 ? '+' : '') + this.phase.toFixed(3);
        }
        
        if (statusPill) {
            const absP = Math.abs(this.phase);
            if (absP < 0.04) {
                statusPill.textContent = '● Primary Transit';
                statusPill.style.background = 'rgba(244, 63, 94, 0.2)';
                statusPill.style.color = '#f43f5e';
            } else if (absP > 0.46) {
                statusPill.textContent = '○ Secondary Eclipse';
                statusPill.style.background = 'rgba(245, 158, 11, 0.2)';
                statusPill.style.color = '#f59e0b';
            } else {
                statusPill.textContent = 'Out of Transit';
                statusPill.style.background = 'rgba(56, 189, 248, 0.15)';
                statusPill.style.color = '#38bdf8';
            }
        }
    }
    
    draw() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        
        ctx.clearRect(0, 0, w, h);
        
        // Orbital Math
        // phase 0.0 = directly in front of star (primary transit)
        // phase +/-0.5 = directly behind star (secondary eclipse)
        const angle = this.phase * 2 * Math.PI;
        const px = cx + this.orbitRadiusX * Math.sin(angle);
        const py = cy + this.orbitRadiusY * Math.cos(angle);
        
        const isPlanetInFront = Math.cos(angle) > 0;
        
        // 1. Draw Orbit Track (Back Half)
        ctx.save();
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.ellipse(cx, cy, this.orbitRadiusX, this.orbitRadiusY, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
        
        // 2. If body is in the back, draw it before the star
        if (!isPlanetInFront) {
            this.drawCompanion(ctx, px, py);
        }
        
        // 3. Draw Host Star
        this.drawStar(ctx, cx, cy);
        
        // 4. If body is in front, draw it over the star
        if (isPlanetInFront) {
            this.drawCompanion(ctx, px, py);
        }
    }
    
    drawStar(ctx, cx, cy) {
        const r = this.starRadius;
        
        // Outer Corona Glow
        const corona = ctx.createRadialGradient(cx, cy, r * 0.7, cx, cy, r * 2.2);
        corona.addColorStop(0, 'rgba(251, 191, 36, 0.6)');
        corona.addColorStop(0.5, 'rgba(245, 158, 11, 0.2)');
        corona.addColorStop(1, 'rgba(245, 158, 11, 0)');
        
        ctx.fillStyle = corona;
        ctx.beginPath();
        ctx.arc(cx, cy, r * 2.2, 0, Math.PI * 2);
        ctx.fill();
        
        // Stellar Photosphere with Limb Darkening
        const starGrad = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.1, cx, cy, r);
        starGrad.addColorStop(0, '#fffbeb');
        starGrad.addColorStop(0.4, '#fef08a');
        starGrad.addColorStop(0.8, '#f59e0b');
        starGrad.addColorStop(1, '#b45309');
        
        ctx.fillStyle = starGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
    }
    
    drawCompanion(ctx, x, y) {
        const bodyRadius = this.isBinary ? 18 : 9;
        
        if (this.isBinary) {
            // Secondary Star (Eclipsing Binary companion)
            const binaryGrad = ctx.createRadialGradient(x - 3, y - 3, 2, x, y, bodyRadius);
            binaryGrad.addColorStop(0, '#fecaca');
            binaryGrad.addColorStop(0.5, '#ef4444');
            binaryGrad.addColorStop(1, '#991b1b');
            
            ctx.fillStyle = binaryGrad;
            ctx.shadowColor = '#ef4444';
            ctx.shadowBlur = 10;
            ctx.beginPath();
            ctx.arc(x, y, bodyRadius, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        } else {
            // Exoplanet Silhouette / Dark Sphere
            const planetGrad = ctx.createRadialGradient(x - 2, y - 2, 1, x, y, bodyRadius);
            planetGrad.addColorStop(0, '#334155');
            planetGrad.addColorStop(0.7, '#0f172a');
            planetGrad.addColorStop(1, '#020617');
            
            ctx.fillStyle = planetGrad;
            ctx.beginPath();
            ctx.arc(x, y, bodyRadius, 0, Math.PI * 2);
            ctx.fill();
            
            // Atmosphere rim
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(x, y, bodyRadius, 0, Math.PI * 2);
            ctx.stroke();
        }
    }
}

// Global instance
window.orbitSim = null;
document.addEventListener('DOMContentLoaded', () => {
    window.orbitSim = new OrbitSimulation('orbit-canvas');
});
