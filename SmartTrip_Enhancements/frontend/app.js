
"use strict";

// SmartTrip frontend logic
const API_BASE = "http://127.0.0.1:8000";

const INTERESTS = [
    ["culture", "Culture"],
    ["adventure", "Adventure"],
    ["nature", "Nature"],
    ["beaches", "Beaches"],
    ["nightlife", "Nightlife"],
    ["cuisine", "Cuisine"],
    ["wellness", "Wellness"],
    ["urban", "Urban experiences"],
    ["seclusion", "Quiet and secluded places"]
];

const SCENIC_IMAGES = [
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=900&q=80"
];

const $ = (id) => document.getElementById(id);

const interestFields = $("interest-fields");
const searchForm = $("search-form");
const recommendForm = $("recommend-form");
const destinationList = $("destination-list");
const resultSummary = $("result-summary");
const loading = $("loading");
const errorMessage = $("error-message");

let selectedDestination = null;
let requestInProgress = false;
let hasUserSearched = false;

// -----------------------------------------------------------------------------
// Interest controls
// -----------------------------------------------------------------------------

function createInterestControls() {
    if (!interestFields || interestFields.children.length > 0) {
        return;
    }

    INTERESTS.forEach(([key, label]) => {
        const wrapper = document.createElement("div");
        wrapper.className = "interest-control";

        const fieldLabel = document.createElement("label");
        fieldLabel.htmlFor = `interest-${key}`;
        fieldLabel.textContent = label;

        const select = document.createElement("select");
        select.id = `interest-${key}`;
        select.name = key;
        select.className = "field-control";
        select.setAttribute("aria-label", `${label} preference`);

        for (let rating = 1; rating <= 5; rating++) {
            const option = document.createElement("option");
            option.value = String(rating);
            option.textContent = `${rating} / 5`;

            if (rating === 3) {
                option.selected = true;
            }

            select.appendChild(option);
        }

        wrapper.append(fieldLabel, select);
        interestFields.appendChild(wrapper);
    });
}

function getInterests() {
    const interests = {};

    INTERESTS.forEach(([key]) => {
        const control = $(`interest-${key}`);
        interests[key] = control ? Number(control.value) : 3;
    });

    return interests;
}

// -----------------------------------------------------------------------------
// Read form settings and update the summary
// -----------------------------------------------------------------------------

function getSelectedScope() {
    return document.querySelector(
        'input[name="destination-scope"]:checked'
    )?.value || "worldwide";
}

function getPreferences() {
    return {
        origin: $("origin")?.value.trim() || "",
        days: Number($("days")?.value || 3),
        travellers: Number($("travellers")?.value || 2),
        budgetStyle: $("budget")?.value || "Mid-range",
        totalBudget: Number($("total-budget")?.value || 0),
        scope: getSelectedScope(),
        travelDates: $("travel-dates")?.value || "flexible",
        interests: getInterests()
    };
}

// The recommendation endpoint used by the original app accepts duration labels.
// Translate the new numeric duration field into those existing labels.
function mapDaysToDuration(days) {
    if (days <= 1) return "Day trip";
    if (days === 2) return "Weekend";
    if (days <= 5) return "Short trip";
    if (days === 7) return "One week";
    return "Long trip";
}

function formatCurrency(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "Not available";
    }

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(number);
}

function updateTripSummary() {
    const preferences = getPreferences();

    if ($("summary-origin")) {
        $("summary-origin").textContent =
            preferences.origin || "Not selected yet";
    }

    if ($("summary-duration")) {
        $("summary-duration").textContent =
            `${preferences.days} ${preferences.days === 1 ? "day" : "days"}`;
    }

    if ($("summary-travellers")) {
        $("summary-travellers").textContent =
            `${preferences.travellers} ${
                preferences.travellers === 1 ? "traveller" : "travellers"
            }`;
    }

    if ($("summary-budget")) {
        $("summary-budget").textContent =
            preferences.totalBudget > 0
                ? formatCurrency(preferences.totalBudget)
                : "Not set";
    }
}

// -----------------------------------------------------------------------------
// Feedback messages
// -----------------------------------------------------------------------------

function showError(message) {
    if (!errorMessage) return;

    errorMessage.textContent = message;
    errorMessage.hidden = false;
    errorMessage.style.display = "block";
}

function clearError() {
    if (!errorMessage) return;

    errorMessage.textContent = "";
    errorMessage.hidden = true;
    errorMessage.style.display = "none";
}

function setLoading(isLoading, message = "Finding destinations...") {
    requestInProgress = isLoading;

    if (loading) {
        loading.textContent = `✦ ${message}`;
        loading.hidden = !isLoading;
        loading.style.display = isLoading ? "block" : "none";
    }

    if (recommendForm) {
        const button = recommendForm.querySelector('button[type="submit"]');

        if (button) {
            button.disabled = isLoading;
            button.setAttribute("aria-busy", String(isLoading));
            button.textContent = isLoading
                ? "Please wait..."
                : "Find my destinations →";
        }
    }

    if (searchForm) {
        const button = searchForm.querySelector('button[type="submit"]');

        if (button) {
            button.disabled = isLoading;
        }
    }
}

function showEmptyState(title, description, icon = "⌖") {
    if (!destinationList) return;

    const state = document.createElement("div");
    state.className = "empty-state";

    const iconBox = document.createElement("div");
    iconBox.className = "empty-state-icon";
    iconBox.setAttribute("aria-hidden", "true");
    iconBox.textContent = icon;

    const heading = document.createElement("h3");
    heading.textContent = title;

    const paragraph = document.createElement("p");
    paragraph.textContent = description;

    state.append(iconBox, heading, paragraph);
    destinationList.replaceChildren(state);
}

// -----------------------------------------------------------------------------
// API helpers
// -----------------------------------------------------------------------------

async function apiGet(endpoint) {
    const response = await fetch(`${API_BASE}${endpoint}`);
    const text = await response.text();

    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = { message: text };
    }

    if (!response.ok) {
        throw new Error(readApiError(data, response.status));
    }

    return data;
}

async function apiPost(endpoint, payload) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const text = await response.text();
    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = { message: text };
    }

    if (!response.ok) {
        throw new Error(readApiError(data, response.status));
    }

    return data;
}

async function lookupAirportCode(location) {
  const params = new URLSearchParams({
    query: location
  });

  const response = await fetch(
    `${API_BASE}/api/airports/resolve?${params.toString()}`
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || `Could not find an airport for "${location}".`
    );
  }

  return data.iata_code;
}

function readApiError(data, status) {
    const detail = data?.detail ?? data?.message ?? data?.error;

    if (Array.isArray(detail)) {
        return `HTTP ${status}: ${detail
            .map(item => item.msg || JSON.stringify(item))
            .join("; ")}`;
    }

    if (typeof detail === "string") {
        return `HTTP ${status}: ${detail}`;
    }

    if (detail !== undefined) {
        return `HTTP ${status}: ${JSON.stringify(detail)}`;
    }

    return `The server returned HTTP ${status}.`;
}

function getDestinationsFromResponse(data) {
    if (Array.isArray(data)) return data;

    if (Array.isArray(data?.destinations)) return data.destinations;
    if (Array.isArray(data?.results)) return data.results;
    if (Array.isArray(data?.recommendations)) return data.recommendations;
    if (Array.isArray(data?.data?.destinations)) return data.data.destinations;

    return [];
}

// -----------------------------------------------------------------------------
// Destination cards
// -----------------------------------------------------------------------------

function getDestinationName(destination) {
    return String(
        destination.city ||
        destination.name ||
        destination.destination ||
        "Destination"
    );
}

function getDestinationCountry(destination) {
    return String(destination.country || "");
}

function addTag(container, text) {
    if (text === null || text === undefined || String(text).trim() === "") {
        return;
    }

    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = String(text);
    container.appendChild(tag);
}

function createDestinationCard(destination, index, method) {
    const card = document.createElement("article");
    card.className = "destination-card";

    // Destination imagery is illustrative because the city dataset does not
    // contain verified destination image URLs.
    const media = document.createElement("div");
    media.className = "destination-card__media";

    const image = document.createElement("img");
    image.src = destination.image_url || SCENIC_IMAGES[index % SCENIC_IMAGES.length];
    image.alt = `Travel inspiration for ${getDestinationName(destination)}`;
    image.loading = "lazy";
    image.decoding = "async";

    image.addEventListener("error", () => {
        image.style.display = "none";
        media.classList.add("destination-card__media--fallback");
    }, { once: true });

    const imageLabel = document.createElement("span");
    imageLabel.className = "destination-card__image-label";
    imageLabel.textContent = "DESTINATION INSPIRATION";

    media.append(image, imageLabel);

    const body = document.createElement("div");
    body.className = "destination-card__body";

    const title = document.createElement("h3");
    title.textContent = getDestinationName(destination);

    const country = document.createElement("p");
    country.className = "destination-country";
    country.textContent = getDestinationCountry(destination);

    const description = document.createElement("p");
    description.className = "destination-description";
    description.textContent =
        destination.short_description ||
        destination.description ||
        "Discover local experiences, scenery and attractions in this destination.";

    const tags = document.createElement("div");
    tags.className = "destination-card__tags";

    addTag(tags, destination.region);
    addTag(tags, destination.budget_level);

    const score = document.createElement("p");
    score.className = "score";

    const numericScore = method === "category-based"
        ? Number(destination.match_score)
        : Number(destination.similarity_score);

    if (Number.isFinite(numericScore)) {
        score.textContent = method === "category-based"
            ? `Preference distance: ${numericScore.toFixed(2)} · lower is better`
            : `Text similarity: ${numericScore.toFixed(3)}`;
    } else {
        score.textContent = "Selected from your travel preferences";
    }

    const actions = document.createElement("div");
    actions.className = "destination-card__actions";

    const planButton = document.createElement("button");
    planButton.className = "button-primary destination-card__plan";
    planButton.type = "button";
    planButton.textContent = "Plan this trip →";

    planButton.addEventListener("click", () => {
        selectDestination(destination);
    });

    actions.appendChild(planButton);
    body.append(title, country, description, tags, score, actions);
    card.append(media, body);

    return card;
}

function displayDestinations(data, method, scope = "worldwide") {
    let destinations = getDestinationsFromResponse(data);

    if (scope === "india") {
        destinations = destinations.filter(destination =>
            getDestinationCountry(destination)
                .toLowerCase()
                .includes("india")
        );

        // Show up to three matches for the India-only option.
        destinations = destinations.slice(0, 3);
    }

    destinationList.replaceChildren();

    if (destinations.length === 0) {
        resultSummary.textContent = "";

        showEmptyState(
            "No matching destinations found",
            scope === "india"
                ? "Try another interest or budget. The current dataset may not contain enough matching Indian destinations."
                : "Try a different search term or adjust your trip preferences.",
            "⌕"
        );
        return;
    }

    const fragment = document.createDocumentFragment();

    destinations.forEach((destination, index) => {
        fragment.appendChild(createDestinationCard(destination, index, method));
    });

    destinationList.appendChild(fragment);

    resultSummary.textContent =
        `Found ${destinations.length} destination${
            destinations.length === 1 ? "" : "s"
        } using ${method === "category-based"
            ? "your travel preferences"
            : "destination search"}.`;
}

// -----------------------------------------------------------------------------
// Destination search and recommendations
// -----------------------------------------------------------------------------

async function sendDestinationRequest(endpoint, payload, method, scope) {
    if (requestInProgress) return;

    clearError();
    hasUserSearched = true;
    setLoading(true, "Finding destinations that fit your preferences...");

    if (resultSummary) {
        resultSummary.textContent = "Searching destinations...";
    }

    showEmptyState(
        "Finding your next destination",
        "SmartTrip is checking available destinations...",
        "✦"
    );

    try {
        const data = await apiPost(endpoint, payload);
        displayDestinations(data, method, scope);
    } catch (error) {
        console.error("SmartTrip destination request failed:", error);

        if (resultSummary) {
            resultSummary.textContent = "Recommendations could not be loaded.";
        }

        showError(
            `${error.message} Make sure the FastAPI backend is running at ${API_BASE}.`
        );

        showEmptyState(
            "We couldn't load destinations",
            "Check the backend terminal for the error, then try again.",
            "!"
        );
    } finally {
        setLoading(false);
    }
}


if (searchForm) {
    searchForm.addEventListener("submit", async event => {
        event.preventDefault();

        const query = $("search-query")?.value.trim() || "";
        const topK = Number($("search-count")?.value || 5);
        const scope = getSelectedScope();

        if (query.length < 2) {
            showError("Please enter at least two characters to search.");
            $("search-query")?.focus();
            return;
        }

        await sendDestinationRequest(
            "/destinations/search",
            {
                query: query,
                top_k: topK
            },
            "content-based",
            scope
        );
    });
}


if (recommendForm) {
    recommendForm.addEventListener("submit", async event => {
        event.preventDefault();

        const preferences = getPreferences();

        if (!preferences.origin) {
            showError("Please enter your starting location.");
            $("origin")?.focus();
            return;
        }

        if (
            !Number.isFinite(preferences.totalBudget) ||
            preferences.totalBudget <= 0
        ) {
            showError("Please enter a total trip budget greater than ₹0.");
            $("total-budget")?.focus();
            return;
        }

        /*
         * Keep this request compatible with the original
         * /destinations/recommend endpoint.
         *
         * Origin, traveller count and the custom total budget are retained
         * for the itinerary and budget steps. The original recommendation
         * endpoint accepts budget style, duration, interests and top_k.
         */
        
        
    
        const payload = {
            budget: preferences.budgetStyle,
            duration: mapDaysToDuration(preferences.days),
            country_scope: preferences.scope,
            interests: preferences.interests,
            top_k: 5
        };

        await sendDestinationRequest(
            "/destinations/recommend",
            payload,
            "category-based",
            preferences.scope
        );


    });
}

// -----------------------------------------------------------------------------
// Budget preset buttons
// -----------------------------------------------------------------------------


const BUDGET_PRESETS = {
    india: {
        short: [10000, 25000, 45000],
        week: [18000, 40000, 75000],
        fortnight: [30000, 70000, 130000],
        month: [55000, 130000, 250000]
    },
    worldwide: {
        short: [60000, 110000, 180000],
        week: [90000, 200000, 350000],
        fortnight: [125000, 275000, 500000],
        month: [200000, 450000, 800000]
    }
};

const BUDGET_STYLES = ["Budget", "Mid-range", "Luxury"];

function getDurationGroup(days) {
    if (days <= 3) return "short";
    if (days <= 7) return "week";
    if (days <= 14) return "fortnight";
    return "month";
}

function getPresetButtons() {
    return Array.from(
        document.querySelectorAll(".preset-button[data-budget]")
    );
}

function refreshBudgetPresets(updateSelectedPreset = true) {
    const buttons = getPresetButtons();
    const budgetInput = $("total-budget");
    const travellers = Math.max(
        1,
        Number($("travellers")?.value || 2)
    );

    const scope = getSelectedScope();
    const days = Math.max(1, Number($("days")?.value || 3));
    const durationGroup = getDurationGroup(days);

    const perPersonAmounts =
        BUDGET_PRESETS[scope][durationGroup];

    // Preserve the selected tier when scope or duration changes.
    const oldAmount = Number(budgetInput?.value || 0);
    const oldSelectedIndex = updateSelectedPreset
        ? buttons.findIndex(
            button => Number(button.dataset.budget) === oldAmount
        )
        : -1;

    buttons.forEach((button, index) => {
        const amount = perPersonAmounts[index] * travellers;

        button.dataset.budget = String(amount);
        button.dataset.style = BUDGET_STYLES[index];

        const title = button.querySelector("strong");
        const subtitle = button.querySelector("small");

        if (title) {
            title.textContent = formatCurrency(amount);
        }

        if (subtitle) {
            subtitle.textContent = [
                "Budget-friendly",
                "Mid-range",
                "Luxury"
            ][index] + " · total trip";
        }
    });

    // If a preset was selected, update it for the new settings.
    if (oldSelectedIndex >= 0 && budgetInput) {
        const newAmount = Number(
            buttons[oldSelectedIndex].dataset.budget
        );

        budgetInput.value = String(newAmount);
        $("budget").value = BUDGET_STYLES[oldSelectedIndex];
    }

    updatePresetSelection();
    updateTripSummary();
}

function updatePresetSelection() {
    const amount = Number($("total-budget")?.value || 0);

    getPresetButtons().forEach(button => {
        const selected = Number(button.dataset.budget) === amount;

        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-pressed", String(selected));
    });
}

function setBudgetPreset(amount, style) {
    const budgetInput = $("total-budget");

    if (budgetInput) {
        budgetInput.value = String(amount);
    }

    if (style && $("budget")) {
        $("budget").value = style;
    }

    updatePresetSelection();
    updateTripSummary();
}

getPresetButtons().forEach(button => {
    button.type = "button";

    button.addEventListener("click", () => {
        const amount = Number(button.dataset.budget);
        const style = button.dataset.style;

        if (Number.isFinite(amount) && amount > 0) {
            setBudgetPreset(amount, style);
        }
    });
});

$("total-budget")?.addEventListener("input", () => {
    updatePresetSelection();

    const amount = Number($("total-budget").value);
    const presetAmounts = getPresetButtons().map(button =>
        Number(button.dataset.budget)
    );

    if (amount > 0) {
        if (amount <= presetAmounts[0]) {
            $("budget").value = "Budget";
        } else if (amount <= presetAmounts[1]) {
            $("budget").value = "Mid-range";
        } else {
            $("budget").value = "Luxury";
        }
    }

    updateTripSummary();
});

// Update the overview when planning inputs change.
["origin", "days", "travellers", "budget", "travel-dates"]
    .forEach(id => {
        $(id)?.addEventListener("input", () => {
            if (id === "days" || id === "travellers") {
                refreshBudgetPresets();
            } else {
                updateTripSummary();
            }
        });

        $(id)?.addEventListener("change", () => {
            if (id === "days" || id === "travellers") {
                refreshBudgetPresets();
            } else {
                updateTripSummary();
            }
        });
    });

document.querySelectorAll(
    'input[name="destination-scope"]'
).forEach(input => {
    input.addEventListener("change", () => {
        refreshBudgetPresets();
    });
});

// Initialise preset labels without changing the user's current budget.
refreshBudgetPresets(false);


// -----------------------------------------------------------------------------
// Itinerary rendering
// -----------------------------------------------------------------------------

function addParagraph(container, text, className = "") {
    if (text === null || text === undefined || String(text).trim() === "") {
        return;
    }

    const paragraph = document.createElement("p");

    if (className) {
        paragraph.className = className;
    }

    paragraph.textContent = String(text);
    container.appendChild(paragraph);
}

function extractItineraryDays(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.days)) return data.days;
    if (Array.isArray(data?.itinerary)) return data.itinerary;
    if (Array.isArray(data?.plan)) return data.plan;
    if (Array.isArray(data?.schedule)) return data.schedule;

    if (data?.itinerary && typeof data.itinerary === "object") {
        if (Array.isArray(data.itinerary.days)) {
            return data.itinerary.days;
        }
    }

    return [];
}

function renderItinerary(data, destination, preferences) {
    const container = $("itinerary-results");
    if (!container) return;

    container.replaceChildren();

    const days = extractItineraryDays(data);

    if (days.length > 0) {
        days.forEach((day, index) => {
            const card = document.createElement("article");
            card.className = "itinerary-day";

            const heading = document.createElement("h4");
            heading.textContent =
                day.title ||
                day.name ||
                (day.day ? `Day ${day.day}` : `Day ${index + 1}`);

            card.appendChild(heading);

            addParagraph(
                card,
                day.description || day.summary || day.overview,
                "itinerary-day__description"
            );

            const activities =
                day.activities ||
                day.places ||
                day.items ||
                day.stops ||
                [];

            if (Array.isArray(activities) && activities.length > 0) {
                const list = document.createElement("ul");

                activities.forEach(activity => {
                    const item = document.createElement("li");

                    if (typeof activity === "string") {
                        item.textContent = activity;
                    } else {
                        const name = activity.name ||
                            activity.title ||
                            activity.place ||
                            activity.activity ||
                            "Activity";

                        const description = activity.description
                            ? ` — ${activity.description}`
                            : "";

                        item.textContent = `${name}${description}`;
                    }

                    list.appendChild(item);
                });

                card.appendChild(list);
            }

            container.appendChild(card);
        });

        return;
    }

    // If the backend returns a different structure, show any useful text fields.
    const summary =
        data?.summary ||
        data?.message ||
        data?.description ||
        data?.detail;

    if (summary && typeof summary === "string") {
        addParagraph(container, summary);
    } else {
        addParagraph(
            container,
            `The backend accepted the itinerary request for ${
                getDestinationName(destination)
            }, but did not return a recognised day-by-day structure.`
        );
    }

    const note = document.createElement("p");
    note.className = "itinerary-note";
    note.textContent =
        "Check the API response in the browser console if the itinerary details are missing.";
    container.appendChild(note);
}

function renderItineraryProblem(destination, error) {
    const container = $("itinerary-results");
    if (!container) return;

    container.replaceChildren();

    const message = document.createElement("div");
    message.className = "inline-alert";
    message.textContent =
        `Destination selected: ${getDestinationName(destination)}. ` +
        `The itinerary request could not be completed: ${error.message}`;

    container.appendChild(message);
}

// -----------------------------------------------------------------------------
// Budget rendering
// -----------------------------------------------------------------------------

function findNumericValue(object, keys) {
    for (const key of keys) {
        const value = object?.[key];

        if (typeof value === "number" && Number.isFinite(value)) {
            return value;
        }

        if (
            typeof value === "string" &&
            value.trim() !== "" &&
            Number.isFinite(Number(value))
        ) {
            return Number(value);
        }
    }

    return null;
}

function appendBudgetRow(tableBody, label, value) {
    const row = document.createElement("tr");
    const labelCell = document.createElement("td");
    const valueCell = document.createElement("td");

    labelCell.textContent = label;
    valueCell.textContent = value;
    row.append(labelCell, valueCell);
    tableBody.appendChild(row);
}

function renderBudget(data, preferences, destination) {
    const summary = $("budget-summary");
    const breakdown = $("budget-breakdown");

    if (!summary || !breakdown) return;

    summary.replaceChildren();
    breakdown.replaceChildren();

    const heading = document.createElement("strong");
    heading.textContent = "Budget overview";
    summary.appendChild(heading);

    const totalEstimate = findNumericValue(data, [
        "total_estimated_cost",
        "estimated_total_cost",
        "estimated_total_trip_cost",
        "total_cost",
        "total"
    ]);

    const localEstimate = findNumericValue(data, [
        "estimated_local_expenses",
        "local_expenses",
        "estimated_cost"
    ]);

    if (totalEstimate !== null) {
        addParagraph(
            summary,
            `Estimated trip total: ${formatCurrency(totalEstimate)}`
        );

        addParagraph(
            summary,
            `Your budget: ${formatCurrency(preferences.totalBudget)}`
        );

        const remaining = preferences.totalBudget - totalEstimate;

        addParagraph(
            summary,
            remaining >= 0
                ? `Estimated money remaining: ${formatCurrency(remaining)}`
                : `Estimated over budget by: ${formatCurrency(Math.abs(remaining))}`
        );

        const perPerson = findNumericValue(data, [
            "per_person",
            "per_person_cost",
            "estimated_per_person"
        ]);

        if (perPerson !== null) {
            addParagraph(
                summary,
                `Estimated per person: ${formatCurrency(perPerson)}`
            );
        }
    } else if (localEstimate !== null) {
        addParagraph(
            summary,
            `Estimated local expenses: ${formatCurrency(localEstimate)}`
        );

        addParagraph(
            summary,
            `Your total budget: ${formatCurrency(preferences.totalBudget)}`
        );

        addParagraph(
            summary,
            "This figure may exclude intercity travel and other items not returned by the backend."
        );
    } else {
        addParagraph(
            summary,
            `Budget entered: ${formatCurrency(preferences.totalBudget)}`
        );

        addParagraph(
            summary,
            `Destination: ${getDestinationName(destination)}`
        );

        addParagraph(
            summary,
            "The API response did not contain a recognised total-cost field."
        );
    }

    const table = document.createElement("table");
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");

    const categoryHeader = document.createElement("th");
    categoryHeader.textContent = "Expense";

    const amountHeader = document.createElement("th");
    amountHeader.textContent = "Estimate";

    headerRow.append(categoryHeader, amountHeader);
    head.appendChild(headerRow);

    const body = document.createElement("tbody");

    const commonCostKeys = [
        ["Intercity travel", ["transport_cost", "estimated_transport_expenses", "estimated_transport", "transport"]],
        ["Accommodation", ["estimated_accommodation", "accommodation_cost", "hotel_cost", "accommodation"]],
        ["Food", ["estimated_food", "food_cost", "food"]],
        ["Local transport", ["estimated_local_transport", "local_transport_cost", "local_transport"]],
        ["Activities", ["estimated_activities", "activity_cost", "activities_cost", "activities"]],
        ["Local expenses", ["estimated_local_expenses", "local_expenses"]]
    ];

    commonCostKeys.forEach(([label, keys]) => {
        const value = findNumericValue(data, keys);

        if (value !== null) {
            appendBudgetRow(body, label, formatCurrency(value));
        }
    });

    const breakdownObject = data?.breakdown || data?.cost_breakdown;

    if (
        breakdownObject &&
        typeof breakdownObject === "object" &&
        !Array.isArray(breakdownObject)
    ) {
        Object.entries(breakdownObject).forEach(([key, value]) => {
            if (typeof value === "number" && Number.isFinite(value)) {
                appendBudgetRow(
                    body,
                    key.replaceAll("_", " "),
                    formatCurrency(value)
                );
            } else if (typeof value === "string") {
                appendBudgetRow(body, key.replaceAll("_", " "), value);
            }
        });
    }

    if (body.children.length > 0) {
        table.append(head, body);
        breakdown.appendChild(table);
    } else {
        addParagraph(
            breakdown,
            "A detailed expense breakdown was not included in the API response."
        );
    }

    const excludes = Array.isArray(data?.excludes) ? data.excludes : [];

    if (excludes.length > 0) {
        addParagraph(breakdown, `May exclude: ${excludes.join(", ")}.`);
    }

    if (data?.is_estimate === true) {
        addParagraph(
            breakdown,
            "These are estimates, not confirmed travel prices."
        );
    }
}

function renderBudgetProblem(preferences, destination, error) {
    const summary = $("budget-summary");
    const breakdown = $("budget-breakdown");

    if (!summary || !breakdown) return;

    summary.replaceChildren();
    breakdown.replaceChildren();

    const heading = document.createElement("strong");
    heading.textContent = "Budget overview";
    summary.appendChild(heading);

    addParagraph(summary, `Your total budget: ${formatCurrency(preferences.totalBudget)}`);
    addParagraph(summary, `Destination: ${getDestinationName(destination)}`);

    addParagraph(
        breakdown,
        `The budget endpoint could not complete the calculation: ${error.message}`
    );

    addParagraph(
        breakdown,
        "No trip cost has been invented. Check the FastAPI terminal for the endpoint error."
    );
}
// City / airport name -> IATA airport code
const AIRPORT_CODES = {
  "chennai": "MAA",
  "mumbai": "BOM",
  "delhi": "DEL",
  "new delhi": "DEL",
  "bengaluru": "BLR",
  "bangalore": "BLR",
  "hyderabad": "HYD",
  "coimbatore": "CJB",
  "kochi": "COK",
  "cochin": "COK",
  "madurai": "IXM",
  "trichy": "TRZ",
  "tiruchirappalli": "TRZ",
  "kolkata": "CCU",
  "pune": "PNQ",
  "ahmedabad": "AMD",
  "goa": "GOI",
  "thiruvananthapuram": "TRV",
  "varanasi": "VNS",
  "singapore": "SIN",
  "dubai": "DXB",
  "london": "LHR",
  "kuala lumpur": "KUL",
  "bangkok": "BKK",
  "doha": "DOH",
  "abu dhabi": "AUH",
  "tokyo": "HND",
  "paris": "CDG"
};

function resolveAirportCode(value) {
  const location = String(value || "").trim();
  const normalized = location.toLowerCase();

  // Already looks like a three-letter IATA code.
  if (/^[a-z]{3}$/i.test(location)) {
    return location.toUpperCase();
  }

  return AIRPORT_CODES[normalized] || null;
}

// -----------------------------------------------------------------------------
// Select destination and request itinerary plus cost estimate
// -----------------------------------------------------------------------------

async function selectDestination(destination) {
    selectedDestination = destination;
    
    // Reuse the origin entered in the main SmartTrip form.
    const mainOrigin = $("origin")?.value.trim() || "";
    const flightOrigin = $("flight-origin");
    const flightDestination = $("flight-destination");

    if (flightOrigin && mainOrigin) {
    const originCode = resolveAirportCode(mainOrigin);

    flightOrigin.value = originCode || mainOrigin;
    }


    // Populate the destination using the airport-resolution API.
    if (flightDestination) {
        const city = getDestinationName(destination);

        flightDestination.value = city;

        try {
            const destinationCode = await lookupAirportCode(city);
            flightDestination.value = destinationCode;
        } catch (error) {
            console.error("Destination airport lookup failed:", error);
            flightDestination.value = city;
        }
    }


    clearError();

    const preferences = getPreferences();
    const city = getDestinationName(destination);
    const country = getDestinationCountry(destination);
    const destinationName = country ? `${city}, ${country}` : city;

    if ($("selected-destination")) {
        $("selected-destination").textContent =
            `${destinationName} · ${preferences.days} day(s) · ` +
            `${preferences.travellers} traveller(s) · ` +
            `${formatCurrency(preferences.totalBudget)} total budget`;
    }

    if ($("itinerary-results")) {
        $("itinerary-results").replaceChildren();

        const message = document.createElement("p");
        message.className = "itinerary-loading";
        message.textContent = `Preparing your trip plan for ${destinationName}...`;

        $("itinerary-results").appendChild(message);
    }

    if ($("budget-summary")) {
        $("budget-summary").textContent = "Calculating estimated trip expenses...";
    }

    if ($("budget-breakdown")) {
        $("budget-breakdown").replaceChildren();
    }

    updateTripSummary();

    $("trip-details")?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    const interests = preferences.interests;

    /*
     * The existing backend includes /trip/itinerary.
     * The request carries common planning fields; if your FastAPI model
     * uses different required names, its validation response will identify them.
     */
    
    const itineraryPayload = {
        destination: destinationName,
        budget_level: preferences.budgetStyle,
        days: Number(preferences.days),
        travellers: Number(preferences.travellers),
        interests: preferences.interests
    };


    
    const budgetPayload = {
        budget: preferences.budgetStyle,
        travellers: Number(preferences.travellers),
        days: Number(preferences.days),
        origin: preferences.origin,
        destination: destinationName,
        budget_limit: Number(preferences.totalBudget),
        round_trip: true
    };

    const itineraryTask = (async () => {
        try {
            let data;

            try {
                data = await apiPost("/trip/itinerary", itineraryPayload);
            } catch (primaryError) {
                // Try the existing builder endpoint if the trip-specific
                // endpoint is missing or doesn't accept this request model.
                if (
                    primaryError.message.includes("HTTP 404") ||
                    primaryError.message.includes("HTTP 405") ||
                    primaryError.message.includes("HTTP 422")
                ) {
                    data = await apiPost("/itinerary/build", itineraryPayload);
                } else {
                    throw primaryError;
                }
            }

            console.log("SmartTrip itinerary response:", data);
            renderItinerary(data, destination, preferences);
        } catch (error) {
            console.error("SmartTrip itinerary error:", error);
            renderItineraryProblem(destination, error);
        }
    })();

    const budgetTask = (async () => {
        try {
            const data = await apiPost("/cost/calculate", budgetPayload);

            console.log("SmartTrip cost response:", data);
            renderBudget(data, preferences, destination);
        } catch (error) {
            console.error("SmartTrip budget error:", error);
            renderBudgetProblem(preferences, destination, error);
        }
    })();

    await Promise.allSettled([itineraryTask, budgetTask]);
}

// -----------------------------------------------------------------------------
// Backend health check
// -----------------------------------------------------------------------------

async function checkBackend() {
    try {
        const data = await apiGet("/health");
        console.info("SmartTrip backend connected:", data);

        // Do not overwrite a user's search results with the health-check message.
        if (!hasUserSearched && resultSummary) {
            const count = data.destinations_loaded;

            resultSummary.textContent =
                typeof count === "number"
                    ? `SmartTrip is ready · ${count} destinations loaded.`
                    : "SmartTrip is connected and ready.";
        }
    } catch (error) {
        console.warn("SmartTrip backend health check failed:", error);

        if (!hasUserSearched) {
            showError(
                "The SmartTrip backend is not connected. Start FastAPI on port 8000, then refresh this page."
            );
        }
    }
}

// Initialise the page.
createInterestControls();
updateTripSummary();
checkBackend();



/* SmartTrip: Ignav live flight search */
const flightForm = document.getElementById("flight-form");

if (flightForm) {
  flightForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    
    const originInput =
      document.getElementById("flight-origin").value.trim();

    const destinationInput =
      document.getElementById("flight-destination").value.trim();
  
    const departureDate =
      document.getElementById("flight-date").value;

    const adults = Number(
      document.getElementById("flight-adults").value
    );

    const message = document.getElementById("flight-message");
    const results = document.getElementById("flight-results");
    const button = document.getElementById("flight-search-button");

    if (!originInput || !destinationInput) {
      message.textContent =
        "Please enter both your departure and destination cities.";
      return;
    }

    if (!departureDate) {
      message.textContent = "Please select a departure date.";
      return;
    }

    results.replaceChildren();
    message.textContent = "Finding airport codes...";
    button.disabled = true;

    try {
      const origin = await lookupAirportCode(originInput);
      const destination = await lookupAirportCode(destinationInput);

      if (origin === destination) {
        throw new Error(
          "Origin and destination airports must be different."
        );
      }

      message.textContent = "Searching Ignav for flight offers...";

      const params = new URLSearchParams({
        origin,
        destination,
        departure_date: departureDate,
        adults: String(adults)
      });

      // The backend calls Ignav. Never expose the API key here.
      const response = await fetch(
        `${API_BASE}/api/flights/live?${params.toString()}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || `Flight search failed (${response.status}).`
        );
      }

      if (
        !Array.isArray(data.itineraries) ||
        data.itineraries.length === 0
      ) {
        message.textContent =
          "No matching flight offers were returned. Try another date or route.";
        return;
      }

      message.textContent =
        `Source: ${data.source || "Ignav"} · ` +
        `Observed at: ${data.observed_at || "Not available"}`;

      data.itineraries.forEach((flight) => {
        const card = document.createElement("article");
        card.className = "flight-result-card";

        const heading = document.createElement("h3");
        heading.textContent =
          flight.airline || "Airline not available";

        const price = document.createElement("p");
        price.textContent =
          flight.price_status === "verified" &&
          Number.isFinite(Number(flight.price))
            ? new Intl.NumberFormat("en-IN", {
                style: "currency",
                currency: flight.currency || "INR",
                maximumFractionDigits: 0
              }).format(Number(flight.price))
            : "Verified fare unavailable";

        const segment = flight.outbound?.segments?.[0];

        const lastSegment =
          flight.outbound?.segments?.[
            (flight.outbound?.segments?.length || 1) - 1
          ];

        const times = document.createElement("p");
        times.textContent = segment
          ? `${segment.departure_airport} ${segment.departure_time_local || ""}` +
            ` → ${lastSegment?.arrival_airport || ""} ` +
            `${lastSegment?.arrival_time_local || ""}`
          : "Flight times unavailable";

        const duration = document.createElement("p");
        const minutes = Number(flight.duration_minutes);

        duration.textContent = Number.isFinite(minutes)
          ? `Duration: ${Math.floor(minutes / 60)}h ${minutes % 60}m`
          : "Duration unavailable";

        const status = document.createElement("p");
        status.textContent =
          flight.price_status === "verified"
            ? "Provider-verified at search time; confirm before booking."
            : "Price not verified; confirm before booking.";

        card.append(heading, price, times, duration, status);
        results.appendChild(card);
      });
    } catch (error) {
      console.error("SmartTrip flight search failed:", error);

      message.textContent =
        error.message || "Unable to retrieve flight offers. Please try again.";
    } finally {
      button.disabled = false;
    }
  });
}

