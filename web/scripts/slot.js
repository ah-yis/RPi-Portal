const glyphButtons = document.querySelectorAll('.glyph-btn');
const figureList = document.getElementById('figureList');
const statusView = document.getElementById('statusView');

const SLOT_RULES = {
	hex: { maxItems: 3, categories: ['playset', 'powerdisc'] },
	p1: { maxItems: 2, categories: ['powerdisc', 'character'] },
	p2: { maxItems: 2, categories: ['powerdisc', 'character'] },
};

const slotState = {
	hex: [],
	p1: [],
	p2: [],
};

let activeSlot = null;
let activePosition = null;

function isHexSlot(slot) {
	return slot === 'hex';
}

function countByCategory(items, category) {
	return items.filter((item) => item.category === category).length;
}

// swapping items shouldnt be illegal, ie if you switch 1 playset 
// ...for another it wont complain
function canAddItem(slot, item, excludingIndex = null) {
	const rules = SLOT_RULES[slot];
	if (!rules) return false;

	const current = slotState[slot].filter((_, i) => i !== excludingIndex);

	if (current.length >= rules.maxItems) return false;
	if (!rules.categories.includes(item.category)) return false;

	if (isHexSlot(slot)) {
		const hasPlayset = countByCategory(current, 'playset') > 0;

		if (item.category === 'playset') return !hasPlayset;
		if (item.category === 'powerdisc') return true;
		return false;
	}

	const hasPlayer = countByCategory(current, 'character') > 0;
	const hasDisc = countByCategory(current, 'powerdisc') > 0;

	if (item.category === 'character') return !hasPlayer;
	if (item.category === 'powerdisc') return hasPlayer && !hasDisc;
	return false;
}

// place/replace an item at a specific position (1-indexed, bottom-to-top)
function setItemAtPosition(slot, position, item) {
	const index = position - 1;

	if (!canAddItem(slot, item, index)) {
		console.warn(`Cannot place ${item.name} (${item.category}) at ${slot} position ${position}`);
		return false;
	}

	slotState[slot][index] = item;
	updateGlyphOccupied(slot);
	if (activeSlot === slot) {
		renderStatusView(slot);
	}
	return true;
}

function removeItemAtPosition(slot, position) {
	const index = position - 1;
	if (!slotState[slot][index]) return;
	slotState[slot].splice(index, 1);
	updateGlyphOccupied(slot);
	if (activeSlot === slot) {
		renderStatusView(slot);
	}
}

function updateGlyphOccupied(slot) {
	const btn = document.querySelector(`.glyph-btn[data-slot="${slot}"]`);
	if (!btn) return;
	btn.dataset.occupied = slotState[slot].length > 0 ? 'true' : 'false';
}

function renderStatusView(slot) {
	const rules = SLOT_RULES[slot];
	if (!rules) return;

	const items = slotState[slot];
	statusView.innerHTML = '';

	for (let position = rules.maxItems; position >= 1; position--) {
		const item = items[position - 1];

		const row = document.createElement('div');
		row.className = 'status-row';
		row.dataset.slot = slot;
		row.dataset.position = position;
		row.dataset.empty = item ? 'false' : 'true';
		row.tabIndex = 0;
		row.setAttribute('role', 'button');
		row.setAttribute(
			'aria-label',
			item ? `${item.name}, position ${position}. Click to replace.` : `Empty, position ${position}. Click to add.`
		);

		const label = document.createElement('span');
		label.className = 'slot-label';
		label.textContent = `Slot ${position}`;

		const value = document.createElement('span');
		value.className = 'value';
		value.textContent = item ? item.name : 'Empty';

		row.appendChild(label);
		row.appendChild(value);

		row.addEventListener('click', () => openFigurePicker(slot, position));
		row.addEventListener('keydown', (e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				openFigurePicker(slot, position);
			}
		});

		statusView.appendChild(row);
	}
}

// opens the figpic to the slot text thing you clicked on
function openFigurePicker(slot, position) {
	activeSlot = slot;
	activePosition = position;

	const rules = SLOT_RULES[slot];
	const existing = slotState[slot][position - 1] || null;

	// categories legal for this position
	const allowedCategories = rules.categories.filter((category) =>
		canAddItem(slot, { category, name: '__probe__' }, position - 1)
	);

	applyCategoryFilter(allowedCategories);
	figureList.dataset.view = 'browse';
}

// called once a figure card in the grid/search is actually clicked
async function pickFigure(item) {
	if (activeSlot === null || activePosition === null) return;

	const slot = activeSlot;
	const position = activePosition;

	// optimistic local update so the status view feels instant
	const ok = setItemAtPosition(slot, position, item);
	if (!ok) return;

	figureList.dataset.view = 'status';
	clearCategoryFilter();
	renderStatusView(slot);
	setStatusRowLoading(slot, position, true);

	try {
		const res = await fetch('/figures/place', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				position: slotToBackendPosition(slot, position),
				filePath: item.binPath,
			}),
		});

		if (!res.ok) {
			const err = await res.json().catch(() => ({}));
			throw new Error(err.detail || `${res.status} ${res.statusText}`);
		}

	} catch (e) {
		console.error(`Failed to place ${item.name} at ${slot}/${position}:`, e);
		removeItemAtPosition(slot, position);
		alert(`Couldn't load "${item.name}" onto the base: ${e.message}`);
	} finally {
		setStatusRowLoading(slot, position, false);
	}
}

function slotToBackendPosition(slot, position) {
	if (slot === 'hex') return position - 1;
	if (slot === 'p1')  return 3 + (position - 1);
	if (slot === 'p2')  return 6 + (position - 1);
	throw new Error(`Unknown slot: ${slot}`);
}

function setStatusRowLoading(slot, position, isLoading) {
	const row = statusView.querySelector(`.status-row[data-slot="${slot}"][data-position="${position}"]`);
	if (!row) return;
	row.dataset.loading = isLoading ? 'true' : 'false';
}

glyphButtons.forEach((btn) => {
	btn.addEventListener('click', () => {
		const slot = btn.dataset.slot;
		const isPressed = btn.getAttribute('aria-pressed') === 'true';

		glyphButtons.forEach((b) => b.setAttribute('aria-pressed', 'false'));

		if (isPressed) {
			activeSlot = null;
			activePosition = null;
			figureList.dataset.view = 'browse';
			clearCategoryFilter();
		} else {
			btn.setAttribute('aria-pressed', 'true');
			activeSlot = slot;
			activePosition = null;
			figureList.dataset.view = 'status';
			renderStatusView(slot);
		}
	});
});