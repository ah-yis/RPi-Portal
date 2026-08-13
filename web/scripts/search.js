const CATEGORY_LABELS = {
	character: 'Characters',
	playset: 'Play Sets',
	powerdisc: 'Power Discs',
	toybox: 'Toy Box Games',
};
const figureSearch = document.getElementById('figureSearch');
const pickerCategories = document.getElementById('pickerCategories');
const pickerGrid = document.getElementById('pickerGrid');
const franchiseSelect = document.getElementById('game');
let CATALOG = [];
let selectedCategory = null;

async function loadCatalog(franchise = 'infinity') {
	pickerGrid.innerHTML = '<div class="picker-empty">Loading figures…</div>';
	try {
		const res = await fetch(`/catalog?franchise=${encodeURIComponent(franchise)}`);
		if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
		CATALOG = await res.json();
	} catch (e) {
		console.error('Failed to load catalog:', e);
		CATALOG = [];
		pickerGrid.innerHTML = `<div class="picker-empty">Couldn't load the figure catalog.</div>`;
		return;
	}
	renderCategoryChips();
	renderGrid();
}

function getAllowedCategories() {
	const raw = figureList.dataset.allowedCategories;
	// "toybox" is a display-only pseudo-category (see matchesCategory) - it's
	// never sent as an actual slot restriction, so drop it when a slot's
	// allowedCategories is set explicitly
	return raw ? raw.split(',').filter(Boolean) : Object.keys(CATEGORY_LABELS);
}

function getAllowedVersion() {
	return figureList.dataset.version || null;
}

// items don't carry category:"toybox" (they're real powerdiscs, per
// SLOT_RULES) - "toybox" as a filter means "powerdisc items whose
// subcategory folder was Toy Box Game"
function matchesCategory(item, category) {
	if (category === 'toybox') {
		return item.category === 'powerdisc' && (item.subcategory || '').toLowerCase().includes('toy box');
	}
	return item.category === category;
}

function renderCategoryChips() {
	const allowed = getAllowedCategories();
	if (selectedCategory && !allowed.includes(selectedCategory) && selectedCategory !== 'toybox') {
		selectedCategory = null;
	}
	pickerCategories.innerHTML = '';
	allowed.forEach((category) => {
		const chip = document.createElement('button');
		chip.type = 'button';
		chip.className = 'category-chip';
		chip.textContent = CATEGORY_LABELS[category] || category;
		chip.dataset.active = selectedCategory === category ? 'true' : 'false';
		chip.addEventListener('click', () => {
			selectedCategory = selectedCategory === category ? null : category;
			renderCategoryChips();
			renderGrid();
		});
		pickerCategories.appendChild(chip);
	});
}

function renderGrid() {
	const allowed = getAllowedCategories();
	const allowedVersion = getAllowedVersion();
	const query = figureSearch.value.trim().toLowerCase();
	const results = CATALOG.filter((item) => {
		const inAllowedSet = allowed.some((category) => matchesCategory(item, category));
		if (!inAllowedSet) return false;
		if (selectedCategory && !matchesCategory(item, selectedCategory)) return false;
		if (allowedVersion && item.version !== allowedVersion) return false;
		if (query && !item.name.toLowerCase().includes(query)) return false;
		return true;
	});
	pickerGrid.innerHTML = '';
	if (results.length === 0) {
		const empty = document.createElement('div');
		empty.className = 'picker-empty';
		empty.textContent = CATALOG.length === 0
			? 'No figures found.'
			: `No figures match "${figureSearch.value}"`;
		pickerGrid.appendChild(empty);
		return;
	}
	results.forEach((item) => {
		const card = document.createElement('button');
		card.type = 'button';
		card.className = 'figure-card';
		const img = document.createElement('img');
		img.src = item.image;
		img.alt = item.name;
		img.loading = 'lazy';
		const name = document.createElement('span');
		name.className = 'figure-card-name';
		name.textContent = item.name;
		card.appendChild(img);
		card.appendChild(name);
		card.setAttribute('aria-label', item.name);
		card.addEventListener('click', () => pickFigure(item));
		pickerGrid.appendChild(card);
	});
}

figureSearch.addEventListener('input', renderGrid);

if (franchiseSelect) {
	franchiseSelect.addEventListener('change', () => {
		loadCatalog(franchiseSelect.value);
	});
}

function applyCategoryFilter(categories) {
	figureList.dataset.allowedCategories = categories.join(',');
	selectedCategory = null;
	renderCategoryChips();
	renderGrid();
}

function clearCategoryFilter() {
	delete figureList.dataset.allowedCategories;
	selectedCategory = null;
	renderCategoryChips();
	renderGrid();
}

loadCatalog(franchiseSelect ? franchiseSelect.value : 'infinity');