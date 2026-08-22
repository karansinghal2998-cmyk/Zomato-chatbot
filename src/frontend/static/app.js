// Zomato AI Web Application Logic (Google Stitch Design Integration)
let currentBudget = 'high';
let selectedCuisines = new Set(['Italian', 'Asian']);

document.addEventListener("DOMContentLoaded", () => {
    fetchLocations();
    // Initialize default selected cuisine pills
    document.querySelectorAll('.cuisine-tag').forEach(tag => {
        const cuisine = tag.textContent.trim();
        if (selectedCuisines.has(cuisine)) {
            tag.classList.add('selected');
        }
    });
    // Trigger initial prediction for Bellandur on page load
    submitPreferences();
});

async function fetchLocations() {
    try {
        const response = await fetch('/api/v1/locations');
        if (response.ok) {
            const data = await response.json();
            const selectEl = document.getElementById('location-select');
            if (data.locations && data.locations.length > 0) {
                selectEl.innerHTML = '';
                data.locations.forEach(loc => {
                    const opt = document.createElement('option');
                    opt.value = loc;
                    opt.textContent = `${loc}, Bangalore`;
                    if (loc.toLowerCase() === 'bellandur') {
                        opt.selected = true;
                    }
                    selectEl.appendChild(opt);
                });
            }
        }
    } catch (e) {
        console.warn("Could not fetch locations dynamically:", e);
    }
}

function setBudget(budgetTier) {
    currentBudget = budgetTier;
    document.querySelectorAll('.budget-btn').forEach(btn => {
        if (btn.dataset.budget === budgetTier) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function updateRatingDisplay(val) {
    document.getElementById('rating-val-display').textContent = `${parseFloat(val).toFixed(1)}+ ⭐`;
}

function toggleCuisine(el, cuisineName) {
    if (selectedCuisines.has(cuisineName)) {
        selectedCuisines.delete(cuisineName);
        el.classList.remove('selected');
    } else {
        selectedCuisines.add(cuisineName);
        el.classList.add('selected');
    }
}

async function submitPreferences() {
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    const submitBtn = document.getElementById('submit-btn');
    const resultsContainer = document.getElementById('results-container');
    const metaBadge = document.getElementById('results-meta-badge');

    // Loading State
    btnText.textContent = "Reasoning with Groq AI...";
    btnSpinner.classList.remove('hidden');
    submitBtn.disabled = true;

    resultsContainer.innerHTML = `
        <div class="glass-panel p-8 rounded-2xl col-span-2 text-center text-slate-400">
            <span class="spinner mb-2"></span>
            <p class="font-outfit text-base text-white font-semibold">Synthesizing Groq LLM Reasoning...</p>
            <p class="text-xs text-slate-400 mt-1">Evaluating candidate restaurants against your criteria</p>
        </div>
    `;

    const locationVal = document.getElementById('location-select').value || 'Bellandur';
    const ratingVal = parseFloat(document.getElementById('rating-slider').value) || 4.2;
    const notesVal = document.getElementById('additional-notes').value || '';

    const payload = {
        location: locationVal,
        budget: currentBudget,
        cuisine: Array.from(selectedCuisines),
        min_rating: ratingVal,
        additional_notes: notesVal
    };

    try {
        const response = await fetch('/api/v1/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();
        metaBadge.innerHTML = `<span class="material-symbols-outlined text-[16px]">memory</span> ${data.total_candidates_evaluated || 6} Candidates Evaluated`;
        renderRecommendations(data.recommendations || []);
    } catch (error) {
        console.error("API Error:", error);
        resultsContainer.innerHTML = `
            <div class="glass-panel p-6 rounded-2xl col-span-2 text-center text-red-400 border border-red-500/30">
                <span class="material-symbols-outlined text-3xl mb-1">warning</span>
                <p class="font-semibold text-sm">Error connecting to Zomato AI Backend: ${error.message}</p>
            </div>
        `;
    } finally {
        btnText.textContent = "Generate AI Recommendations";
        btnSpinner.classList.add('hidden');
        submitBtn.disabled = false;
    }
}

function renderRecommendations(recs) {
    const resultsContainer = document.getElementById('results-container');
    resultsContainer.innerHTML = '';

    if (!recs || recs.length === 0) {
        resultsContainer.innerHTML = `
            <div class="glass-panel p-8 rounded-2xl col-span-2 text-center text-slate-400">
                <p class="text-sm">No matching restaurants found. Try adjusting your locality or rating threshold!</p>
            </div>
        `;
        return;
    }

    recs.forEach(rec => {
        const cuisinesHTML = (rec.cuisines || [])
            .map(c => `<span class="bg-white/5 border border-white/10 px-2.5 py-1 rounded text-xs text-slate-300">${c}</span>`)
            .join('');

        const rankBadgeColor = rec.rank === 1 ? 'text-amber-400 border-amber-400/30' : 'text-slate-300 border-white/20';

        const cardHTML = `
            <div class="recommendation-card hover:border-zomato-glow/50 transition-all duration-300">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <span class="bg-black/60 backdrop-blur-md px-2.5 py-0.5 rounded-md font-bold text-xs border ${rankBadgeColor} inline-block mb-1.5">
                            #${rec.rank} Match
                        </span>
                        <h4 class="font-outfit text-xl font-bold text-white">${rec.restaurant_name}</h4>
                    </div>
                    <div class="bg-zomato-green text-white px-2.5 py-1 rounded-md font-bold text-sm flex items-center gap-1 shadow-lg">
                        ${parseFloat(rec.rating).toFixed(1)} <span class="material-symbols-outlined text-[14px]">star</span>
                    </div>
                </div>

                <div class="flex items-center gap-4 text-xs text-slate-400 mb-3">
                    <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px] text-zomato-red">location_on</span> ${rec.locality}</span>
                    <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px] text-zomato-red">payments</span> ${rec.estimated_cost_for_two} for two</span>
                </div>

                <div class="flex flex-wrap gap-1.5 mb-4">
                    ${cuisinesHTML}
                </div>

                <div class="ai-reason-box">
                    <h5 class="text-zomato-glow text-[11px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                        <span class="material-symbols-outlined text-[14px]">lightbulb</span> GROQ AI EXPLANATION
                    </h5>
                    <p class="text-xs text-slate-300 leading-relaxed">
                        ${rec.ai_explanation}
                    </p>
                </div>
            </div>
        `;
        resultsContainer.innerHTML += cardHTML;
    });
}
