// HTML5 Live Geolocation Detection with Automatic Desktop/IP Fallback
window.initGroundXPlaces = function () {
    const initialize = () => {
        const input = document.getElementById('placeSearchInput');
        const status = document.getElementById('placeSearchStatus');
        if (!input || !window.google?.maps?.places?.Autocomplete) return;
        const autocomplete = new google.maps.places.Autocomplete(input, {
            fields: ['geometry', 'name', 'address_components'],
            types: ['geocode']
        });
        autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            const point = place.geometry && place.geometry.location;
            if (!point) {
                if (status) status.textContent = 'Choose a suggested location from the list.';
                return;
            }
            const locality = (place.address_components || []).find(component =>
                component.types.includes('locality') || component.types.includes('administrative_area_level_2')
            );
            const city = locality?.long_name || place.name || 'Selected Location';
            const url = new URL(window.location.href);
            url.searchParams.set('lat', point.lat().toFixed(6));
            url.searchParams.set('lon', point.lng().toFixed(6));
            url.searchParams.set('city', city);
            window.location.href = url.toString();
        });
        if (status) status.textContent = '';
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, { once: true });
    } else {
        initialize();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btnDetectGps = document.getElementById('btnDetectGps');
    const modalGpsBtn = document.getElementById('modalGpsBtn');
    const locModal = document.getElementById('locationModal');

    function resetButton() {
        if (btnDetectGps) {
            btnDetectGps.innerHTML = '<i class="fa-solid fa-crosshairs"></i> Nearby';
        }
        if (modalGpsBtn) {
            modalGpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use Live GPS Coordinates';
        }
    }

    function applyCoordinates(lat, lon, cityName = 'My Location') {
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('lat', parseFloat(lat).toFixed(6));
        currentUrl.searchParams.set('lon', parseFloat(lon).toFixed(6));
        currentUrl.searchParams.set('city', cityName);
        window.location.href = currentUrl.toString();
    }

    // Fallback: IP-based Geolocation (works seamlessly on Desktops/Laptops without GPS chips)
    function fallbackIpLocation() {
        fetch('https://get.geojs.io/v1/ip/geo.json')
            .then(res => res.json())
            .then(data => {
                if (data && data.latitude && data.longitude) {
                    const city = data.city || 'My Location';
                    applyCoordinates(data.latitude, data.longitude, city);
                } else {
                    fallbackDefaultCity();
                }
            })
            .catch(() => {
                fallbackDefaultCity();
            });
    }

    function fallbackDefaultCity() {
        resetButton();
        if (locModal) locModal.style.display = 'none';
        // Default to Kolhapur coordinates smoothly
        applyCoordinates(16.6956, 74.2317, 'Kolhapur');
    }

    function detectUserLocation() {
        if (btnDetectGps) btnDetectGps.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Locating...';
        if (modalGpsBtn) modalGpsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Locating...';

        if (!navigator.geolocation) {
            fallbackIpLocation();
            return;
        }

        // Use enableHighAccuracy: false so desktop computers without satellite GPS chips don't time out
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                applyCoordinates(lat, lon, 'My Location');
            },
            (error) => {
                console.warn('Browser GPS unavailable, using network IP fallback:', error.message);
                // Gracefully fallback via IP network location without blocking popup alert
                fallbackIpLocation();
            },
            {
                enableHighAccuracy: false, // Critical for desktops/laptops!
                timeout: 6000,
                maximumAge: 300000 // Cache for 5 minutes
            }
        );
    }

    if (btnDetectGps) btnDetectGps.addEventListener('click', detectUserLocation);
    if (modalGpsBtn) modalGpsBtn.addEventListener('click', detectUserLocation);
});