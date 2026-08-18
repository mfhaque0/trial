/* static/js/script.js */

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initCalculator();
});

// ============================================================================
// PART 1: NAVIGATION MENU
// ============================================================================
function initNavigation() {
    const menuToggle = document.querySelector(".menu-toggle");
    const mainNav = document.querySelector("#main-nav");

    if (!menuToggle || !mainNav) return;

    function closeMenu() {
        mainNav.classList.remove("active");
        menuToggle.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
        mainNav.classList.add("active");
        menuToggle.setAttribute("aria-expanded", "true");
    }

    // Toggle button click
    menuToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
        if (isExpanded) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    // Close when clicking a navigation link
    mainNav.addEventListener("click", (e) => {
        if (e.target.tagName.toLowerCase() === "a") {
            closeMenu();
        }
    });

    // Close on Escape key press
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
            if (isExpanded) {
                closeMenu();
                menuToggle.focus(); // Return focus for accessibility
            }
        }
    });

    // Close when clicking outside the navigation area
    document.addEventListener("click", (e) => {
        const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
        if (isExpanded && !mainNav.contains(e.target) && e.target !== menuToggle) {
            closeMenu();
        }
    });
}

// ============================================================================
// PART 2: CALCULATOR LOGIC
// ============================================================================
function initCalculator() {
    const form = document.querySelector("#calculator-form");
    if (!form) return;

    // Default Macros Setup (60/20/20)
    const carbsInput = document.querySelector("#carbs");
    const proteinInput = document.querySelector("#protein");
    const fatInput = document.querySelector("#fat");

    if (carbsInput && carbsInput.value === "55") carbsInput.value = "60";
    if (proteinInput && proteinInput.value === "15") proteinInput.value = "20";
    if (fatInput && fatInput.value === "30") fatInput.value = "20";

    // Elements - Height
    const heightUnit = document.querySelector("#height-unit");
    const heightInput = document.querySelector("#height");
    const heightSingle = document.querySelector("#height-single");
    const heightFeet = document.querySelector("#height-feet");
    const feetInput = document.querySelector("#height-feet-value");
    const inchesInput = document.querySelector("#height-inches-value");

    // Elements - Weight
    const weightUnit = document.querySelector("#weight-unit");
    const weightInput = document.querySelector("#weight");

    // Elements - Goal Logic
    const goalInput = document.querySelector("#goal");
    const deficitField = document.querySelector("#deficit-field");
    const surplusField = document.querySelector("#surplus-field");

    // Elements - Advanced Section Logic
    const proteinMethod = document.querySelector("#protein-method");
    const proteinGPerKgField = document.querySelector("#protein-g-per-kg-field");
    const proteinCustomGField = document.querySelector("#protein-custom-g-field");

    const fluidMethod = document.querySelector("#fluid-method");
    const customFluidField = document.querySelector("#custom-fluid-field");

    // Elements - UI
    const errorBox = document.querySelector("#calculator-error");
    const resultPanel = document.querySelector("#result-panel");
    const resultsContent = document.querySelector("#results-content");
    const submitButton = form.querySelector('button[type="submit"]');

    // ------------------------------------------------------------------------
    // Utility functions
    // ------------------------------------------------------------------------
    function showError(message) {
        if (!errorBox) return;
        errorBox.textContent = message;
        errorBox.classList.add("visible");
        errorBox.style.display = "block";
    }

    function clearError() {
        if (!errorBox) return;
        errorBox.textContent = "";
        errorBox.classList.remove("visible");
        errorBox.style.display = "none";
    }

    function escapeHTML(str) {
        if (typeof str !== "string") return str;
        return str.replace(/[&<>'"]/g, tag => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "'": "&#39;",
            '"': "&quot;"
        }[tag]));
    }

    // ------------------------------------------------------------------------
    // Goal Toggling
    // ------------------------------------------------------------------------
    function updateGoalVisibility() {
        if (!goalInput || !deficitField || !surplusField) return;
        deficitField.hidden = goalInput.value !== "loss";
        surplusField.hidden = goalInput.value !== "gain";
    }

    if (goalInput) {
        goalInput.addEventListener("change", updateGoalVisibility);
        updateGoalVisibility();
    }

    // ------------------------------------------------------------------------
    // Advanced Toggling (Protein & Fluid)
    // ------------------------------------------------------------------------
    function updateProteinVisibility() {
        if (!proteinMethod || !proteinGPerKgField || !proteinCustomGField) return;
        proteinGPerKgField.hidden = proteinMethod.value !== "g_per_kg";
        proteinCustomGField.hidden = proteinMethod.value !== "custom_g";
    }

    function updateFluidVisibility() {
        if (!fluidMethod || !customFluidField) return;
        customFluidField.hidden = fluidMethod.value !== "custom";
    }

    if (proteinMethod) {
        proteinMethod.addEventListener("change", updateProteinVisibility);
        updateProteinVisibility();
    }

    if (fluidMethod) {
        fluidMethod.addEventListener("change", updateFluidVisibility);
        updateFluidVisibility();
    }
    // ------------------------------------------------------------------------
    // Height Unit Switching + Real Conversion
    // ------------------------------------------------------------------------

    function getHeightInCm(unit = heightUnit?.value) {
        if (!unit) return null;

        if (unit === "cm") {
            const value = parseFloat(heightInput?.value);
            return Number.isFinite(value) && value > 0 ? value : null;
        }

        if (unit === "m") {
            const value = parseFloat(heightInput?.value);
            return Number.isFinite(value) && value > 0
                ? value * 100
                : null;
        }

        if (unit === "inches") {
            const value = parseFloat(heightInput?.value);
            return Number.isFinite(value) && value > 0
                ? value * 2.54
                : null;
        }

        if (unit === "ft + inches") {
            const feet = parseFloat(feetInput?.value) || 0;
            const inches = parseFloat(inchesInput?.value) || 0;

            if (feet <= 0 && inches <= 0) {
                return null;
            }

            return ((feet * 12) + inches) * 2.54;
        }

        return null;
    }


    function setHeightFromCm(cm, unit) {
        if (!Number.isFinite(cm) || cm <= 0) return;

        if (unit === "cm") {
            if (heightInput) {
                heightInput.value = Number(cm.toFixed(1));
            }
            return;
        }

        if (unit === "m") {
            if (heightInput) {
                heightInput.value = Number((cm / 100).toFixed(2));
            }
            return;
        }

        if (unit === "inches") {
            if (heightInput) {
                heightInput.value = Number((cm / 2.54).toFixed(1));
            }
            return;
        }

        if (unit === "ft + inches") {
            const totalInches = cm / 2.54;
            const feet = Math.floor(totalInches / 12);
            const inches = totalInches - (feet * 12);

            if (feetInput) {
                feetInput.value = feet;
            }

            if (inchesInput) {
                inchesInput.value = Number(inches.toFixed(1));
            }
        }
    }


    function updateHeightVisibility() {
        if (!heightUnit || !heightSingle || !heightFeet) return;

        const unit = heightUnit.value;

        if (unit === "ft + inches") {
            heightSingle.hidden = true;
            heightFeet.hidden = false;

            if (heightInput) {
                heightInput.required = false;
            }

            if (feetInput) {
                feetInput.required = true;
            }

            if (inchesInput) {
                inchesInput.required = false;
            }

            return;
        }

        heightSingle.hidden = false;
        heightFeet.hidden = true;

        if (heightInput) {
            heightInput.required = true;

            if (unit === "cm") {
                heightInput.placeholder = "e.g. 165";
            } else if (unit === "m") {
                heightInput.placeholder = "e.g. 1.65";
            } else if (unit === "inches") {
                heightInput.placeholder = "e.g. 65";
            }
        }

        if (feetInput) {
            feetInput.required = false;
        }

        if (inchesInput) {
            inchesInput.required = false;
        }
    }


    if (heightUnit) {
        let previousHeightUnit = heightUnit.value;

        heightUnit.addEventListener("change", () => {
            // Read the existing value using the PREVIOUS unit.
            const currentCm = getHeightInCm(previousHeightUnit);

            // Switch the visible fields.
            updateHeightVisibility();

            // Convert the value into the NEW unit.
            if (currentCm !== null) {
                setHeightFromCm(currentCm, heightUnit.value);
            }

            // Remember the new unit for the next conversion.
            previousHeightUnit = heightUnit.value;
        });

        updateHeightVisibility();
    }


    // ------------------------------------------------------------------------
    // Weight Unit Switching + Real Conversion
    // ------------------------------------------------------------------------

    function getWeightInKg(unit = weightUnit?.value) {
        if (!weightInput || !unit) return null;

        const value = parseFloat(weightInput.value);

        if (!Number.isFinite(value) || value <= 0) {
            return null;
        }

        if (unit === "lb") {
            return value * 0.45359237;
        }

        return value;
    }


    function setWeightFromKg(kg, unit) {
        if (!weightInput || !Number.isFinite(kg) || kg <= 0) {
            return;
        }

        if (unit === "lb") {
            weightInput.value = Number(
                (kg / 0.45359237).toFixed(1)
            );
        } else {
            weightInput.value = Number(
                kg.toFixed(1)
            );
        }
    }


    function updateWeightVisibility() {
        if (!weightUnit || !weightInput) return;

        if (weightUnit.value === "kg") {
            weightInput.placeholder = "e.g. 60";
        } else if (weightUnit.value === "lb") {
            weightInput.placeholder = "e.g. 132";
        }
    }


    if (weightUnit) {
        let previousWeightUnit = weightUnit.value;

        weightUnit.addEventListener("change", () => {
            // Read the existing value using the PREVIOUS unit.
            const currentKg = getWeightInKg(previousWeightUnit);

            // Update placeholder.
            updateWeightVisibility();

            // Convert the value into the NEW unit.
            if (currentKg !== null) {
                setWeightFromKg(currentKg, weightUnit.value);
            }

            // Remember the new unit.
            previousWeightUnit = weightUnit.value;
        });

        updateWeightVisibility();
    }

    // Clear errors on input
    form.addEventListener("input", clearError);

    // ------------------------------------------------------------------------
    // Form Submission & API Call
    // ------------------------------------------------------------------------
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearError();

        // Safe reads for primary elements
        const nameInput = document.querySelector("#patient-name");
        const ageInput = document.querySelector("#age");
        const sexInput = document.querySelector("#sex");
        const activityRadio = document.querySelector('input[name="activity"]:checked');

        // Validation: Required Basics
        if (!nameInput || !nameInput.value.trim()) return showError("Please enter the patient's name.");
        if (!ageInput || !ageInput.value || parseFloat(ageInput.value) <= 0) return showError("Please enter a valid age.");
        if (!weightInput || !weightInput.value || parseFloat(weightInput.value) <= 0) return showError("Please enter a valid weight.");
        if (!activityRadio) return showError("Please select an activity level.");

        // Validation: Height
        if (heightUnit && heightUnit.value === "ft + inches") {
            if (!feetInput || !feetInput.value) return showError("Please enter height in feet.");
        } else {
            if (!heightInput || !heightInput.value || parseFloat(heightInput.value) <= 0) return showError("Please enter a valid height.");
        }

        // Validation: Macros (Must = 100%)
        const c = parseFloat(carbsInput ? carbsInput.value : 0) || 0;
        const p = parseFloat(proteinInput ? proteinInput.value : 0) || 0;
        const f = parseFloat(fatInput ? fatInput.value : 0) || 0;

        if (Math.abs((c + p + f) - 100) > 0.01) {
            return showError("Macro percentages (Carbs + Protein + Fat) must total exactly 100%.");
        }

        // Construct Request Payload
        const payload = {
            patient_name: nameInput.value.trim(),
            age: parseFloat(ageInput.value),
            sex: sexInput ? sexInput.value : "female",

            weight_unit: weightUnit ? weightUnit.value : "kg",
            weight: parseFloat(weightInput.value),

            height_unit: heightUnit ? heightUnit.value : "cm",

            activity: activityRadio.value,
            goal: goalInput ? goalInput.value : "maintain",

            carbs_pct: c,
            protein_pct: p,
            fat_pct: f
        };

        // Attach conditional height
        if (payload.height_unit === "ft + inches") {
            payload.height_feet = parseFloat(feetInput.value);
            payload.height_inches = parseFloat(inchesInput.value) || 0;
        } else {
            payload.height = parseFloat(heightInput.value);
        }

        // Attach conditional goal requirements
        if (payload.goal === "loss") {
            const def = document.querySelector("#custom-deficit");
            payload.custom_deficit = def ? parseFloat(def.value) : 500;
        } else if (payload.goal === "gain") {
            const sur = document.querySelector("#custom-surplus");
            payload.custom_surplus = sur ? parseFloat(sur.value) : 300;
        }

        // Attach Advanced Section Logic
        if (proteinMethod) {
            payload.protein_method = proteinMethod.value;
            if (payload.protein_method === "g_per_kg") {
                const pkg = document.querySelector("#protein-g-per-kg");
                payload.protein_g_per_kg = pkg ? parseFloat(pkg.value) : 0.8;
            } else if (payload.protein_method === "custom_g") {
                const pcg = document.querySelector("#protein-custom-g");
                payload.protein_custom_g = pcg ? parseFloat(pcg.value) : 0;
            }
        }

        if (fluidMethod) {
            payload.fluid_method = fluidMethod.value;
            if (payload.fluid_method === "custom") {
                const cFluid = document.querySelector("#custom-fluid");
                payload.custom_fluid_ml_per_kg = cFluid ? parseFloat(cFluid.value) : 30;
            }
        }

        // Attach Clinical Details
        const preg = document.querySelector("#pregnancy-status");
        if (preg && preg.value) payload.pregnancy_status = preg.value;

        const lact = document.querySelector("#lactation-status");
        if (lact && lact.value) payload.lactation_status = lact.value;

        const diet = document.querySelector("#dietary-preference");
        if (diet && diet.value) payload.dietary_preference = diet.value;

        const med = document.querySelector("#medical-condition");
        if (med && med.value) payload.medical_condition = med.value;

        const notes = document.querySelector("#medical-notes");
        if (notes && notes.value) payload.medical_notes = notes.value;

        // UI Loading State
        const originalButtonText = submitButton.textContent;
        submitButton.textContent = "Calculating...";
        submitButton.disabled = true;

        try {
            // Pointing to /api/assessments/calculate as requested
            const response = await fetch("/api/assessments/calculate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error ||
                    "Unable to calculate nutrition estimates at this time."
                );
            }

            sessionStorage.setItem(
                "nutritionAssessment",
                JSON.stringify({
                    patient: payload.patient_name,
                    data: data
                })
            );

            window.location.href = "/calculators/assessment-result";

        } catch (error) {
            showError(error.message || "An unexpected error occurred.");
        } finally {
            submitButton.textContent = originalButtonText;
            submitButton.disabled = false;
        }
    });

    // ------------------------------------------------------------------------
    // Result Rendering (Matches backend calculations response)
    // ------------------------------------------------------------------------
    function renderResults(data) {
        if (!resultPanel || !resultsContent) return;

        let warningsHTML = "";
        if (data.warnings && Array.isArray(data.warnings) && data.warnings.length > 0) {
            warningsHTML = `<div class="premium-alert premium-warning" style="background:#fff7ed; padding:12px; margin-bottom:16px; border-left:4px solid #ea580c;">
                <strong>⚠️ Clinical Notices:</strong>
                <ul style="margin-top: 8px; padding-left: 20px;">
                    ${data.warnings.map(w => `<li>${escapeHTML(typeof w === "string" ? w : (w.message || "Review needed"))}</li>`).join('')}
                </ul>
            </div>`;
        }

        // Extract values using the current backend response structure.
        const pGrams = data.macros?.protein?.grams ?? data.protein ?? 0;
        const pPct = data.macros?.protein?.percentage ?? data.protein_pct ?? 0;

        const cGrams =
            data.macros?.carbohydrate?.grams ??
            data.carbohydrate ??
            0;

        const cPct =
            data.macros?.carbohydrate?.percentage ??
            data.carbs_pct ??
            0;

        const fGrams = data.macros?.fat?.grams ?? data.fat ?? 0;
        const fPct =
            data.macros?.fat?.percentage ??
            data.fat_pct ??
            0;

        const fluidTarget =
            data.fluid?.target_l ??
            data.water_litres ??
            0;

        const fluidRange =
            data.fluid?.estimated_l_range
                ? `${data.fluid.estimated_l_range[0]}–${data.fluid.estimated_l_range[1]} L/day`
                : "N/A";

        resultsContent.innerHTML = `
            ${warningsHTML}
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
                <div style="padding: 16px; background: var(--paper); border: 1px solid var(--line); border-radius: 8px;">
                    <small style="color: var(--muted); text-transform: uppercase;">BMI</small>
                    <div style="font-size: 1.5rem; font-weight: bold;">${(data.bmi?.value || data.bmi || 0).toFixed(1)}</div>
                    <small style="color: var(--muted);">${escapeHTML(data.bmi?.category || data.bmi_category || "Standard")}</small>
                </div>
                <div style="padding: 16px; background: var(--paper); border: 1px solid var(--line); border-radius: 8px;">
                    <small style="color: var(--muted); text-transform: uppercase;">Ideal Body Weight</small>
                    <div style="font-size: 1.5rem; font-weight: bold;">${data.ibw?.value ?? data.ideal_body_weight ?? "—"} <span style="font-size: 1rem;">kg</span></div>
                </div>
                <div style="padding: 16px; background: var(--paper); border: 1px solid var(--line); border-radius: 8px;">
                    <small style="color: var(--muted); text-transform: uppercase;">REE / BMR</small>
                    <div style="font-size: 1.5rem; font-weight: bold;">${data.bmr || data.ree || 0}</div>
                    <small style="color: var(--muted);">kcal/day</small>
                </div>
                <div style="padding: 16px; background: var(--paper); border: 1px solid var(--line); border-radius: 8px;">
                    <small style="color: var(--muted); text-transform: uppercase;">TDEE (Maintenance)</small>
                    <div style="font-size: 1.5rem; font-weight: bold;">${data.tdee || 0}</div>
                    <small style="color: var(--muted);">kcal/day</small>
                </div>
            </div>

            <div style="padding: 24px; background: var(--sage); border-radius: 8px; margin-bottom: 24px;">
                <p class="eyebrow" style="margin-bottom: 4px; color: var(--sage-text);">DAILY CALORIE TARGET</p>
                <div style="font-size: 2.5rem; font-weight: bold; color: var(--ink); margin-bottom: 8px;">
                    ${data.target || data.target_calories || 0} <span style="font-size: 1.2rem; font-weight: normal;">kcal/day</span>
                </div>
            </div>

            <h3 style="font-family: Georgia, serif; margin-bottom: 16px; border-bottom: 1px solid var(--line); padding-bottom: 8px;">Macronutrients</h3>
            
            <div style="display: grid; gap: 12px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
                    <strong>Protein (${pPct}%)</strong>
                    <span>${pGrams} g/day</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
                    <strong>Carbohydrate (${cPct}%)</strong>
                    <span>${cGrams} g/day</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
                    <strong>Fat (${fPct}%)</strong>
                    <span>${fGrams} g/day</span>
                </div>
            </div>

            <h3 style="font-family: Georgia, serif; margin-bottom: 16px; border-bottom: 1px solid var(--line); padding-bottom: 8px;">Fluid Requirement</h3>
            <div style="margin-bottom: 24px;">
                <div style="font-size: 1.2rem; font-weight: bold;">Target: ${typeof fluidTarget === 'number' ? fluidTarget.toFixed(1) : fluidTarget} L/day</div>
                <div style="color: var(--muted); font-size: 0.9rem;">Estimated Range: ${fluidRange}</div>
            </div>

            <div style="background: #f8fafc; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0; font-size: 0.85rem; color: #475569;">
                <strong>Note:</strong> These calculations are estimates based on standard clinical formulas and do not replace professional clinical judgment. Adjust targets based on ongoing patient monitoring.
            </div>
        `;

        resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

/* ============================================================
   IFCT 2017 FOOD DATABASE
   ============================================================ */

(() => {
    const searchInput = document.getElementById("ifct-search");
    const categorySelect = document.getElementById("ifct-category");
    const resultsContainer = document.getElementById("ifct-results");

    if (!searchInput || !categorySelect || !resultsContainer) {
        return;
    }

    let searchTimer = null;

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatNumber(value) {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        const number = Number(value);

        if (!Number.isFinite(number)) {
            return "—";
        }

        return number
            .toFixed(2)
            .replace(/\.00$/, "")
            .replace(/(\.\d)0$/, "$1");
    }


    /*
     * Calories:
     * Display using 3 significant digits.
     *
     * Examples:
     * 125       → 125
     * 139.818   → 140
     * 320.27    → 320
     * 103.489   → 103
     */
    function formatCalories(value) {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        const number = Number(value);

        if (!Number.isFinite(number)) {
            return "—";
        }

        return Number(number.toPrecision(3)).toString();
    }


    function renderResults(foods) {

        if (!foods.length) {

            resultsContainer.innerHTML = `
            <div class="ifct-status">
                No IFCT foods found.
            </div>
        `;

            return;
        }


        resultsContainer.innerHTML = `

        <div class="ifct-card-grid">

            ${foods.map(food => `

                <article class="ifct-result-card">

                    <!-- FOOD HEADER -->

                    <div class="ifct-result-header">

                        <div class="ifct-result-title">

                            <h3>
                                ${escapeHtml(food.name)}
                            </h3>

                            <p>
                                ${escapeHtml(
            food.category || "Uncategorized"
        )}
                            </p>

                        </div>

                        <div class="ifct-serving">
                            100 g
                        </div>

                    </div>


                    <!-- NUTRITION -->

                    <div class="ifct-nutrition-grid">

                        <div class="ifct-nutrition-box calories">

                            <strong>
                                ${formatCalories(food.calories)}
                            </strong>

                            <small>
                                kcal
                            </small>

                        </div>


                        <div class="ifct-nutrition-box">

                            <strong>
                                ${formatNumber(food.protein)}
                            </strong>

                            <small>
                                Protein · g
                            </small>

                        </div>


                        <div class="ifct-nutrition-box">

                            <strong>
                                ${formatNumber(food.carbohydrates)}
                            </strong>

                            <small>
                                Carbs · g
                            </small>

                        </div>


                        <div class="ifct-nutrition-box">

                            <strong>
                                ${formatNumber(food.fat)}
                            </strong>

                            <small>
                                Fat · g
                            </small>

                        </div>


                        <div class="ifct-nutrition-box">

                            <strong>
                                ${formatNumber(food.fiber)}
                            </strong>

                            <small>
                                Fiber · g
                            </small>

                        </div>

                    </div>


                    <!-- FOOTER -->

                    <div class="ifct-result-footer">

                        <span>
                            Nutritional values per serving
                        </span>

                        <button
                            type="button"
                            class="button ifct-details-button"
                            data-food-id="${food.id}"
                        >
                            View details
                        </button>

                    </div>

                </article>

            `).join("")}

        </div>

    `;
    }

    

    // Bind "View details" buttons rendered directly in the
    // server-side "Your database" table.
    function bindStaticFoodDetailButtons() {
    document
        .querySelectorAll(".ifct-details-button")
        .forEach(button => {
            if (button.dataset.detailsBound === "true") {
                return;
            }

            button.dataset.detailsBound = "true";

            button.addEventListener("click", () => {
                const foodId = button.dataset.foodId;

                if (foodId) {
                    loadFoodDetails(foodId);
                }
            });
        });
}

async function loadFoodDetails(foodId) {
    resultsContainer.innerHTML = `
            <div class="ifct-status">
                Loading complete IFCT details...
            </div>
        `;

    try {
        const response = await fetch(
            `/api/foods/${encodeURIComponent(foodId)}`,
            {
                headers: {
                    "Accept": "application/json"
                }
            }
        );

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(
                data.error || `HTTP ${response.status}`
            );
        }

        const data = await response.json();

        renderFoodDetails(
            data.food,
            data.components || []
        );

    } catch (error) {
        console.error(
            "IFCT food details failed:",
            error
        );

        resultsContainer.innerHTML = `
                <div class="ifct-status">
                    Unable to load food details.
                    Please try again.
                </div>
            `;
    }
}

function renderFoodDetails(food, components) {
    const grouped = {};

    for (const component of components) {
        const category = component.category || "other";

        if (!grouped[category]) {
            grouped[category] = [];
        }

        grouped[category].push(component);
    }

    const categoryLabels = {
        proximate: "Proximate Composition",
        energy: "Energy",
        carbohydrate: "Carbohydrate",
        dietary_fibre: "Dietary Fibre",
        oligosaccharide: "Oligosaccharides",
        phytate: "Phytate",
        phytosterol: "Phytosterols",
        saponin: "Saponins",
        fatty_acid: "Fatty Acids",
        other: "Other Components"
    };

    const categoryOrder = [
        "proximate",
        "energy",
        "carbohydrate",
        "dietary_fibre",
        "oligosaccharide",
        "phytate",
        "phytosterol",
        "saponin",
        "fatty_acid",
        "other"
    ];

    const sections = categoryOrder
        .filter(category => grouped[category]?.length)
        .map(category => `
                <section class="ifct-detail-section">

                    <h3>
                        ${escapeHtml(
            categoryLabels[category] || category
        )}
                    </h3>

                    <div class="ifct-component-grid">

                        ${grouped[category].map(component => {

            const belowLimit =
                component.measurement_status ===
                "below_detection_limit";

            let value = "—";

            if (belowLimit) {
                value = "Below detectable limit";
            } else if (
                component.value !== null &&
                component.value !== undefined
            ) {
                value = formatNumber(
                    component.value
                );

                if (
                    component.standard_deviation !== null &&
                    component.standard_deviation !== undefined
                ) {
                    value +=
                        ` ± ${formatNumber(
                            component.standard_deviation
                        )}`;
                }
            }

            return `
                                <div class="ifct-component">

                                    <div>
                                        <strong>
                                            ${escapeHtml(
                component.name
            )}
                                        </strong>

                                        <small>
                                            ${escapeHtml(
                component.code || ""
            )}
                                        </small>
                                    </div>

                                    <div class="ifct-component-value">
                                        <strong>
                                            ${escapeHtml(value)}
                                        </strong>

                                        ${belowLimit
                    ? ""
                    : `<small>${escapeHtml(
                        component.unit || ""
                    )}</small>`
                }
                                    </div>

                                </div>
                            `;
        }).join("")}

                    </div>

                </section>
            `)
        .join("");

    resultsContainer.innerHTML = `
            <div class="ifct-detail-card">

                <div class="ifct-detail-header">

                    <div>
                        <p class="eyebrow">
                            ICMR-NIN IFCT 2017
                        </p>

                        <h2>
                            ${escapeHtml(food.name)}
                        </h2>

                        <p class="ifct-food-meta">
                            ${escapeHtml(
        food.source_food_code || ""
    )}
                            ·
                            ${escapeHtml(
        food.category || "Uncategorized"
    )}
                        </p>
                    </div>

                    <button
                        type="button"
                        class="button ifct-back-button"
                        id="ifct-back-to-results"
                    >
                        Back to results
                    </button>

                </div>

                <div class="ifct-basic-grid">

                    <div class="ifct-nutrient">
                        <strong>${formatNumber(food.calories)}</strong>
                        <small>kcal</small>
                    </div>

                    <div class="ifct-nutrient">
                        <strong>${formatNumber(food.protein)}</strong>
                        <small>protein g</small>
                    </div>

                    <div class="ifct-nutrient">
                        <strong>${formatNumber(food.carbohydrates)}</strong>
                        <small>carbs g</small>
                    </div>

                    <div class="ifct-nutrient">
                        <strong>${formatNumber(food.fat)}</strong>
                        <small>fat g</small>
                    </div>

                    <div class="ifct-nutrient">
                        <strong>${formatNumber(food.fiber)}</strong>
                        <small>fibre g</small>
                    </div>

                </div>

                ${sections || `
                    <div class="ifct-status">
                        No additional component data reported.
                    </div>
                `}

                <div class="ifct-source-note">
                    Source:
                    ${escapeHtml(
        food.source_name ||
        "ICMR-NIN IFCT 2017"
    )}

                    ${food.source_version
            ? ` · ${escapeHtml(
                food.source_version
            )}`
            : ""
        }

                    ${food.regions_count
            ? ` · ${escapeHtml(
                String(food.regions_count)
            )} regions`
            : ""
        }
                </div>

            </div>
        `;

    const backButton =
        document.getElementById(
            "ifct-back-to-results"
        );

    if (backButton) {
        backButton.addEventListener(
            "click",
            loadFoods
        );
    }
}

// Bind buttons already rendered by templates/foods.html.
bindStaticFoodDetailButtons();

async function loadFoods() {
    const query = searchInput.value.trim();
    const category = categorySelect.value;

    resultsContainer.innerHTML = `
            <div class="ifct-status">
                Searching IFCT database...
            </div>
        `;

    try {
        const params = new URLSearchParams();

        if (query) {
            params.set("q", query);
        }

        if (category) {
            params.set("category", category);
        }

        params.set("limit", "100");

        const response = await fetch(
            `/api/foods?${params.toString()}`,
            {
                headers: {
                    "Accept": "application/json"
                }
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        renderResults(data.foods || []);

    } catch (error) {
        console.error("IFCT food search failed:", error);

        resultsContainer.innerHTML = `
                <div class="ifct-status">
                    Unable to load the IFCT food database.
                    Please try again.
                </div>
            `;
    }
}

async function loadCategories() {
    try {
        const response = await fetch("/api/foods?limit=100");

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        const categories = [
            ...new Set(
                (data.foods || [])
                    .map(food => food.category)
                    .filter(Boolean)
            )
        ].sort();

        for (const category of categories) {
            const option = document.createElement("option");

            option.value = category;
            option.textContent = category;

            categorySelect.appendChild(option);
        }

    } catch (error) {
        console.error(
            "Unable to load IFCT categories:",
            error
        );
    }
}

searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(
        loadFoods,
        300
    );
});

categorySelect.addEventListener(
    "change",
    loadFoods
);

loadCategories();

}) ();