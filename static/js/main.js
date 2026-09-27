// Main Application Interactivity
document.addEventListener('DOMContentLoaded', () => {
    // 1. Slot Booking Matrix Selection
    const slotBtns = document.querySelectorAll('.slot-btn');
    const selectedSlotInput = document.getElementById('selectedSlotInput');
    const sumSlotLabel = document.getElementById('sumSlotLabel');
    const sumRateLabel = document.getElementById('sumRateLabel');
    const btnSubmitBooking = document.getElementById('btnSubmitBooking');
    const hourlyRate = Number(sumRateLabel?.dataset.hourlyRate || 0);

    if (slotBtns.length > 0) {
        slotBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.disabled) return;
                // Deselect previous
                slotBtns.forEach(b => b.classList.remove('selected'));
                // Select clicked
                btn.classList.add('selected');
                const slotId = btn.getAttribute('data-slot-id');
                const slotTime = btn.querySelector('.slot-time').textContent.trim();
                const durationHours = Number(btn.dataset.durationHours || 1);

                if (selectedSlotInput) selectedSlotInput.value = slotId;
                if (sumSlotLabel) sumSlotLabel.innerHTML = `Selected Slot: <strong>${slotTime}</strong>`;
                if (sumRateLabel) sumRateLabel.textContent = `Total: ₹${(hourlyRate * durationHours).toFixed(0)} (${durationHours} hours)`;
                if (btnSubmitBooking) btnSubmitBooking.removeAttribute('disabled');
            });
        });
    }

    const refreshAvailability = async () => {
        const grids = document.querySelectorAll('[data-availability-url]');
        await Promise.all([...grids].map(async (grid) => {
            const url = new URL(grid.dataset.availabilityUrl, window.location.origin);
            url.searchParams.set('date', grid.dataset.bookingDate);
            try {
                const response = await fetch(url);
                if (!response.ok) return;
                const availability = await response.json();
                const slotsById = new Map(availability.slots.map((slot) => [String(slot.id), slot.is_booked]));
                grid.querySelectorAll('[data-slot-id]').forEach((element) => {
                    const isBooked = slotsById.get(element.dataset.slotId);
                    if (isBooked === undefined) return;
                    if (element.matches('.slot-btn')) {
                        element.classList.toggle('booked', isBooked);
                        element.classList.toggle('available', !isBooked);
                        element.disabled = isBooked;
                        element.title = isBooked ? 'Already booked by another player' : '';
                        const status = element.querySelector('.slot-status-text');
                        if (status) status.innerHTML = isBooked
                            ? '<i class="fa-solid fa-lock"></i> Booked'
                            : '<i class="fa-solid fa-circle-check"></i> Available';
                        if (isBooked && element.classList.contains('selected')) {
                            element.classList.remove('selected');
                            if (selectedSlotInput) selectedSlotInput.value = '';
                            if (sumSlotLabel) sumSlotLabel.textContent = 'Select a slot above';
                            if (sumRateLabel) sumRateLabel.textContent = `Select a slot to see the total. Rate: ₹${hourlyRate}/hour`;
                            if (btnSubmitBooking) btnSubmitBooking.disabled = true;
                        }
                    } else {
                        element.classList.toggle('occupied', isBooked);
                        element.classList.toggle('free', !isBooked);
                        const status = element.querySelector('.gm-status-pill');
                        if (status) status.innerHTML = isBooked
                            ? '<i class="fa-solid fa-user-check"></i> Booked'
                            : '<i class="fa-solid fa-circle"></i> Available';
                    }
                });
            } catch (error) {
                console.error('Could not refresh slot availability.', error);
            }
        }));
    };
    if (document.querySelector('[data-availability-url]')) {
        window.setInterval(refreshAvailability, 10000);
    }

    // 2. Location Modal Toggle
    const locModal = document.getElementById('locationModal');
    const locPickerBtn = document.getElementById('locPickerBtn');
    const locPickerBtn2 = document.getElementById('locPickerBtn2');
    const closeLocModal = document.getElementById('closeLocModal');

    const openModal = () => {
        if (locModal) locModal.style.display = 'flex';
    };
    const closeModal = () => {
        if (locModal) locModal.style.display = 'none';
    };

    if (locPickerBtn) locPickerBtn.addEventListener('click', openModal);
    if (locPickerBtn2) locPickerBtn2.addEventListener('click', openModal);
    if (closeLocModal) closeLocModal.addEventListener('click', closeModal);

    if (locModal) {
        locModal.addEventListener('click', (e) => {
            if (e.target === locModal) closeModal();
        });
    }
});
