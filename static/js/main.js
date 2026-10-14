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
                if (sumRateLabel) sumRateLabel.textContent = `Total: \u20B9${(hourlyRate * durationHours).toFixed(0)} (${durationHours} hours)`;
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
                            if (sumRateLabel) sumRateLabel.textContent = `Select a slot to see the total. Rate: \u20B9${hourlyRate}/hour`;
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
// Equipment selection and itemized booking total.
document.addEventListener('DOMContentLoaded', () => {
    const inputs = [...document.querySelectorAll('[data-equipment-quantity]')];
    const slots = [...document.querySelectorAll('.slot-btn')];
    const rateLabel = document.getElementById('sumRateLabel');
    if (!inputs.length || !rateLabel) return;

    const hourlyRate = Number(rateLabel.dataset.hourlyRate || 0);
    let selectedDuration = 0;

    const updateTotal = () => {
        const groundTotal = hourlyRate * selectedDuration;
        const equipmentTotal = inputs.reduce((sum, input) =>
            sum + Number(input.value || 0) * Number(input.dataset.unitPrice || 0), 0);
        if (selectedDuration) {
            rateLabel.textContent = 'Ground: \u20B9' + groundTotal.toFixed(2) +
                ' + Equipment: \u20B9' + equipmentTotal.toFixed(2) +
                ' = Total: \u20B9' + (groundTotal + equipmentTotal).toFixed(2);
        }
    };

    const applyAvailability = (slot, availability) => {
        inputs.forEach((input) => {
            const itemId = input.dataset.equipmentId;
            const remaining = Math.max(0, Number(availability[itemId] ?? input.dataset.stockQuantity ?? 0));
            input.max = String(remaining);
            input.disabled = remaining === 0;
            if (Number(input.value) > remaining) input.value = String(remaining);
            const stockLabel = input.closest('[data-equipment-item]')?.querySelector('[data-equipment-stock-label]');
            if (stockLabel) {
                stockLabel.textContent = remaining
                    ? remaining + ' available for this slot'
                    : 'None available for this slot';
            }
        });
        selectedDuration = Number(slot.dataset.durationHours || 1);
        updateTotal();
    };

    inputs.forEach((input) => {
        input.addEventListener('input', () => {
            const maximum = Number(input.max || input.dataset.stockQuantity || 0);
            const requested = Number(input.value || 0);
            if (requested > maximum) {
                input.value = String(maximum);
                const stockLabel = input.closest('[data-equipment-item]')?.querySelector('[data-equipment-stock-label]');
                if (stockLabel) stockLabel.textContent = 'Maximum ' + maximum + ' available for this slot';
            } else if (requested < 0) {
                input.value = '0';
            }
            updateTotal();
        });
    });
    slots.forEach((slot) => {
        slot.addEventListener('click', () => {
            if (slot.disabled) return;
            let availability = {};
            try {
                availability = JSON.parse(slot.dataset.equipmentAvailability || '{}');
            } catch (error) {
                console.error('Could not read equipment availability.', error);
            }
            applyAvailability(slot, availability);
        });
    });

    const availabilityGrid = document.querySelector('[data-availability-url]');
    if (availabilityGrid) {
        window.setInterval(async () => {
            const selected = slots.find((slot) => slot.classList.contains('selected'));
            if (!selected) return;
            const url = new URL(availabilityGrid.dataset.availabilityUrl, window.location.origin);
            url.searchParams.set('date', availabilityGrid.dataset.bookingDate);
            try {
                const response = await fetch(url);
                if (!response.ok) return;
                const payload = await response.json();
                const state = payload.slots.find((slot) => String(slot.id) === selected.dataset.slotId);
                if (state?.equipment_available) applyAvailability(selected, state.equipment_available);
            } catch (error) {
                console.error('Could not refresh equipment stock.', error);
            }
        }, 10000);
    }
});
