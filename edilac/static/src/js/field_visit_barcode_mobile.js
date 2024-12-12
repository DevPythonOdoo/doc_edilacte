$(document).ready(function () {
    let selectedDeviceId;

    function decodeOnce(codeReader, selectedDeviceId) {
        codeReader
            .decodeFromInputVideoDevice(selectedDeviceId, "field_visit_video")
            .then((result) => {
                // -------------------------------------
                // Write scanned value in input field and trigger events
                // -------------------------------------
                var el = document.getElementById("scanned_qr_code");
                el.value = result.text;
                el.dispatchEvent(new InputEvent("input", { bubbles: true }));
                el.dispatchEvent(new InputEvent("enter", { bubbles: true }));
                el.dispatchEvent(new InputEvent("change", { bubbles: true }));
                // -------------------------------------

                // Reset reader
                codeReader.reset();

                // Hide video and stop button
                $("#js_id_field_visit_video_div").hide();
                $("#js_id_field_visit_stop_btn").hide();

                // Display scanned result
                document.getElementById("js_id_field_visit_result").textContent = result.text;
            })
            .catch((err) => {
                console.error(err);
            });
    }

    function decodeContinuously(codeReader, selectedDeviceId) {
        codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, "field_visit_video", (result, err) => {
            if (result) {
                // -------------------------------------
                // Write scanned value in input field and trigger events
                // -------------------------------------
                var el = document.getElementById("scanned_qr_code");
                el.value = result.text;
                el.dispatchEvent(new InputEvent("input", { bubbles: true }));
                el.dispatchEvent(new InputEvent("enter", { bubbles: true }));
                el.dispatchEvent(new InputEvent("change", { bubbles: true }));
                // -------------------------------------

                // Display scanned result
                document.getElementById("js_id_field_visit_result").textContent = result.text;
            }

            if (err) {
                if (err instanceof ZXing.NotFoundException) {
                    console.log("No QR code found.");
                } else if (err instanceof ZXing.ChecksumException) {
                    console.log("A code was found, but its checksum was invalid.");
                } else if (err instanceof ZXing.FormatException) {
                    console.log("A code was found, but it was in an invalid format.");
                }
            }
        });
    }

    // Initialize the QR code reader
    const codeReader = new ZXing.BrowserMultiFormatReader();
    console.log("FieldVisit QR Code Reader initialized");

    // Fetch video input devices
    codeReader
        .getVideoInputDevices()
        .then((result) => {
            const sourceSelect = document.getElementById("js_id_field_visit_camera_select");

            result.forEach((item) => {
                const sourceOption = document.createElement("option");
                sourceOption.text = item.label;
                sourceOption.value = item.deviceId;
                sourceSelect.appendChild(sourceOption);
            });

            // Handle camera selection
            $(document).on("change", "#js_id_field_visit_camera_select", function (ev) {
                selectedDeviceId = $(ev.currentTarget).val();
                $("#js_id_field_visit_stop_btn").click();
                $("#js_id_field_visit_start_btn").click();
            });

            // Start scanning on button click
            $(document).on("click", "#js_id_field_visit_start_btn", function () {
                var el = document.getElementById("scanned_qr_code");
                el.value = '';
                el.dispatchEvent(new InputEvent("input", { bubbles: true }));
                el.dispatchEvent(new InputEvent("enter", { bubbles: true }));
                el.dispatchEvent(new InputEvent("change", { bubbles: true }));

                $("#js_id_field_visit_video_div").show();
                $("#js_id_field_visit_stop_btn").show();

                if ($('div[name="continuous_scan"] span:contains("True")').length) {
                    decodeContinuously(codeReader, selectedDeviceId);
                } else {
                    decodeOnce(codeReader, selectedDeviceId);
                }
            });

            // Stop scanning on button click
            $(document).on("click", "#js_id_field_visit_stop_btn", function () {
                document.getElementById("js_id_field_visit_result").textContent = "";
                var el = document.getElementById("scanned_qr_code");
                el.value = '';
                el.dispatchEvent(new InputEvent("input", { bubbles: true }));
                el.dispatchEvent(new InputEvent("enter", { bubbles: true }));
                el.dispatchEvent(new InputEvent("change", { bubbles: true }));

                codeReader.reset();
                $("#js_id_field_visit_video_div").hide();
                $("#js_id_field_visit_stop_btn").hide();
            });
        })
        .catch((err) => {
            console.error("Error initializing QR code reader:", err);
        });

    // Hide the stop button by default
    $("#js_id_field_visit_stop_btn").hide();
});
