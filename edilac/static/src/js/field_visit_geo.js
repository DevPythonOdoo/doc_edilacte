/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";

const capturePosition = async (notification, rpc, record) => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            try {
                await rpc({
                    model: "field.visit",
                    method: "write",
                    args: [
                        [record.res_id], // ID du record
                        {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                        },
                    ],
                });
                notification.add("Position capturée et enregistrée avec succès.", { type: "success" });
            } catch (error) {
                notification.add("Erreur lors de la mise à jour des coordonnées : " + error.message, { type: "danger" });
            }
        });
    } else {
        notification.add("Géolocalisation non supportée.", { type: "danger" });
    }
};

export default capturePosition;
