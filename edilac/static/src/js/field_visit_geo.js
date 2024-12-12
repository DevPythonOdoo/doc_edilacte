/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";

const capturePosition = async (notification, rpc, recordId) => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                try {
                    alert(capturePosition)
                    // Passer les coordonnées au backend via RPC
                    await rpc({
                        model: "crm.lead",
                        method: "capture_position",
                        args: [recordId, {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude
                        }],
                    });
                    notification.add("Position capturée et enregistrée avec succès.", { type: "success" });
                } catch (error) {
                    notification.add("Erreur lors de l'enregistrement de la position : " + error.message, { type: "danger" });
                }
            },
            (error) => {
                notification.add(`Erreur de géolocalisation : ${error.message}`, { type: "danger" });
            }
        );


    } else {
        notification.add("La géolocalisation n'est pas prise en charge par ce navigateur.", { type: "danger" });
    }
};

export default capturePosition;
