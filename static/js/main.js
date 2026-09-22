// Main Application Interactivity
document.addEventListener('DOMContentLoaded', () => {
    // 1. Slot Booking Matrix Selection
    const slotBtns = document.querySelectorAll('.slot-btn.available');
    const selectedSlotInput = document.getElementById('selectedSlotInput');
    const sumSlotLabel = document.getElementById('sumSlotLabel');
    const btnSubmitBooking = document.getElementById('btnSubmitBooking');

    if (slotBtns.length > 0) {
        slotBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Deselect previous
                slotBtns.forEach(b => b.classList.remove('selected'));
                // Select clicked
                btn.classList.add('selected');
                const slotId = btn.getAttribute('data-slot-id');
                const slotTime = btn.querySelector('.slot-time').textContent.trim();

                if (selectedSlotInput) selectedSlotInput.value = slotId;
                if (sumSlotLabel) sumSlotLabel.innerHTML = `Selected Slot: <strong>${slotTime}</strong>`;
                if (btnSubmitBooking) btnSubmitBooking.removeAttribute('disabled');
            });
        });
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
