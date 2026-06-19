const form = document.querySelector("#matchForm");
const artistList = document.querySelector("#artistList");
const feeDistribution = document.querySelector("#feeDistribution");
const matchReasons = document.querySelector("#matchReasons");
const distanceSlider = document.querySelector("#distanceSlider");
const distanceOutput = document.querySelector("#distanceOutput");
const savedCount = document.querySelector("#savedCount");
const showMoreButton = document.querySelector("#showMoreButton");

let recommendations = [];
let visibleArtists = 5;
let favorites = new Set(JSON.parse(localStorage.getItem("gigevateFavorites") || "[]"));

function euro(value) {
  if (value === null || value === undefined || value === "") return "Unknown";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function initials(name) {
  return String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function formPayload() {
  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  payload.onlyAvailable = form.elements.onlyAvailable.checked;
  payload.onlyWithinBudget = form.elements.onlyWithinBudget.checked;
  payload.topN = 50;
  return payload;
}

async function loadOptions() {
  const response = await fetch("/api/options");
  const data = await response.json();

  fillSelect("#genreSelect", data.genres, "Techno");
  fillSelect("#eventTypeSelect", data.eventTypes, "Club night");
  fillDatalist("#cityOptions", data.cities);
}

function fillSelect(selector, values, fallback) {
  const select = document.querySelector(selector);
  const current = select.value || fallback;
  const options = [current, ...values.filter((value) => value !== current)];
  select.innerHTML = options
    .filter(Boolean)
    .slice(0, 80)
    .map((value) => `<option>${escapeHtml(value)}</option>`)
    .join("");
  select.value = current;
}

function fillDatalist(selector, values) {
  document.querySelector(selector).innerHTML = values
    .filter(Boolean)
    .slice(0, 100)
    .map((value) => `<option value="${escapeHtml(value)}"></option>`)
    .join("");
}

async function requestMatches() {
  setLoading();
  const response = await fetch("/api/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formPayload()),
  });
  const data = await response.json();
  if (!response.ok || data.error) {
    throw new Error(data.error || "Recommendation request failed");
  }

  recommendations = data.recommendations || [];
  visibleArtists = 5;
  renderSummary(data.summary, data.filters, data.event);
  renderArtists();
  renderReasons(recommendations[0], data.filters, data.event);
  renderFeeDistribution(data.summary.fee_distribution || []);
}

function setLoading() {
  artistList.innerHTML = `<div class="empty-state">Calculating matches...</div>`;
}

function renderSummary(summary, filters, event) {
  document.querySelector("#artistsFound").textContent = summary.artists_found;
  document.querySelector("#withinBudget").textContent = summary.within_budget;
  document.querySelector("#availableCount").textContent = summary.available;
  document.querySelector("#strongMatches").textContent = summary.strong_matches;
  document.querySelector("#budgetLabel").textContent = `${euro(filters.budgetMin)} - ${euro(filters.budgetMax)}`;
  document.querySelector("#dateLabel").textContent = event.DateTimeStart
    ? new Date(event.DateTimeStart).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    : "No date";
  document.querySelector("#feeTotalLabel").textContent = `${summary.artists_found} artists`;
}

function renderArtists() {
  if (!recommendations.length) {
    artistList.innerHTML = `<div class="empty-state">No artists found within these filters.</div>`;
    showMoreButton.hidden = true;
    return;
  }

  artistList.innerHTML = recommendations.slice(0, visibleArtists).map(renderArtistRow).join("");
  showMoreButton.hidden = visibleArtists >= recommendations.length;
}

function renderArtistRow(artist) {
  const score = Math.round((Number(artist.final_score) || 0) * 100);
  const saved = favorites.has(String(artist.ArtistId));
  const statusClass = artist.available ? "status-ok" : "status-warn";
  const statusText = artist.available ? "Available" : "Unavailable";
  const fee = artist.total_fee || artist.AvgBookingFee;
  const tags = [artist.MainGenres, artist.SubGenres, artist.location_reason]
    .filter(Boolean)
    .flatMap((value) => String(value).split(","))
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, 3);

  return `
    <article class="artist-row">
      <div class="rank">${artist.rank}</div>
      <div class="artist-image">${escapeHtml(initials(artist.ArtistName))}</div>
      <div class="artist-meta">
        <h3>${escapeHtml(artist.ArtistName)}</h3>
        <p>${escapeHtml(artist.MainGenres || "Genre unknown")} · ${escapeHtml(artist.CurrentLocation || artist.City || "Location unknown")}</p>
        <div class="chip-row">${tags.map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}</div>
      </div>
      <div class="score-ring" style="--score:${score}%"><span>${score}%</span></div>
      <div class="fee-block">
        <strong>${euro(fee)}</strong>
        <small>Fee</small>
        <div class="${statusClass}">${statusText}</div>
      </div>
      <button class="save-button ${saved ? "saved" : ""}" type="button" data-id="${artist.ArtistId}" aria-label="Save">♡</button>
    </article>
  `;
}

function renderReasons(artist, filters, event) {
  if (!artist) {
    matchReasons.innerHTML = `<div class="empty-state">No match selected.</div>`;
    return;
  }

  const reasons = [
    ["Genre match", artist.genre_reason || event.MainGenres, artist.genre_score >= 0.5],
    ["Fee fits budget", `${euro(filters.budgetMin)} - ${euro(filters.budgetMax)}`, artist.budget_check === "Ja"],
    ["Artist is available", document.querySelector("#dateLabel").textContent, artist.available],
    ["Travel distance is acceptable", artist.distance_km ? `${artist.distance_km} km` : artist.location_reason, artist.location_score >= 0.2],
  ];

  matchReasons.innerHTML = reasons
    .map(
      ([title, detail, ok]) => `
        <div class="reason-item">
          <div class="reason-icon">${ok ? "OK" : "!"}</div>
          <div>
            <strong>${escapeHtml(title)}</strong>
            <small>${escapeHtml(detail || "")}</small>
          </div>
          <span class="${ok ? "status-ok" : "status-warn"}">${ok ? "✓" : "!"}</span>
        </div>
      `,
    )
    .join("");
}

function renderFeeDistribution(rows) {
  if (!rows.length) {
    feeDistribution.innerHTML = `<div class="empty-state">No fee data available.</div>`;
    return;
  }

  const max = Math.max(...rows.map((row) => row.count), 1);
  feeDistribution.innerHTML = rows
    .map(
      (row) => `
        <div class="bar-row">
          <span>${escapeHtml(row.label)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.max(4, (row.count / max) * 100)}%"></div></div>
          <span>${row.count}</span>
        </div>
      `,
    )
    .join("");
}

function updateSavedCount() {
  savedCount.textContent = `You have saved ${favorites.size} artists`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

distanceSlider.addEventListener("input", () => {
  distanceOutput.textContent = `${distanceSlider.value} km`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await requestMatches();
  } catch (error) {
    artistList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
});

artistList.addEventListener("click", (event) => {
  const button = event.target.closest(".save-button");
  if (!button) return;
  const id = String(button.dataset.id);
  if (favorites.has(id)) {
    favorites.delete(id);
  } else {
    favorites.add(id);
  }
  localStorage.setItem("gigevateFavorites", JSON.stringify([...favorites]));
  updateSavedCount();
  renderArtists();
});

showMoreButton.addEventListener("click", () => {
  visibleArtists += 5;
  renderArtists();
});

document.querySelector("#resetFilters").addEventListener("click", () => {
  form.reset();
  distanceOutput.textContent = `${distanceSlider.value} km`;
});

document.querySelector("#newEventButton").addEventListener("click", () => {
  form.elements.eventName.focus();
});

updateSavedCount();
loadOptions()
  .then(requestMatches)
  .catch((error) => {
    artistList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  });
