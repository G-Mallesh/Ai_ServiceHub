console.log("AI Service Hub loaded");


function getCustomerLocation() {

    if (!navigator.geolocation) {

        alert(
            "Geolocation is not supported by your browser."
        );

        return;
    }

    navigator.geolocation.getCurrentPosition(

        function(position) {

            const latitude =
                position.coords.latitude;

            const longitude =
                position.coords.longitude;


            const latitudeInput =
                document.getElementById("latitude");

            const longitudeInput =
                document.getElementById("longitude");


            if (latitudeInput) {
                latitudeInput.value = latitude;
            }

            if (longitudeInput) {
                longitudeInput.value = longitude;
            }


            alert(
                "Current location detected."
            );
        },

        function(error) {

            alert(
                "Unable to get your location. " +
                "Please allow location access."
            );

        }
    );
}


function getBookingLocation() {

    if (!navigator.geolocation) {

        alert(
            "Geolocation is not supported."
        );

        return;
    }


    navigator.geolocation.getCurrentPosition(

        function(position) {

            const latitude =
                position.coords.latitude;

            const longitude =
                position.coords.longitude;


            const latitudeInput =
                document.getElementById(
                    "customer_latitude"
                );

            const longitudeInput =
                document.getElementById(
                    "customer_longitude"
                );


            if (latitudeInput) {

                latitudeInput.value =
                    latitude;
            }


            if (longitudeInput) {

                longitudeInput.value =
                    longitude;
            }


            alert(
                "Booking location detected."
            );
        },

        function(error) {

            alert(
                "Please allow browser location access."
            );

        }
    );
}