document.querySelector('button[aria-label="Reboot"]').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to reboot?')) return;

	try {
		const res = await fetch('/system/reboot', { method: 'POST' });
		const data = await res.json();
		alert(data.message || 'Rebooting...');
	} catch (e) {
		alert('Something went wrong...');
	}
});

document.querySelector('button[aria-label="Shutdown"]').addEventListener('click', async () => {
	if (!confirm('Are you sure you want to turn it off?')) return;

	try {
		const res = await fetch('/system/shutdown', { method: 'POST' });
		const data = await res.json();
		alert(data.message || 'Shutting down...');
	} catch (e) {
		alert('Something went wrong...');
    }
});