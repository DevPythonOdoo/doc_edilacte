/** @odoo-module **/

import { registry } from "@web/core/registry";
import capturePosition from "./field_visit_geo";

const captureGeoPositionButton = {
    dependencies: ["notification", "rpc"],
    async setup(env) {
        const notification = useService("notification");
        const rpc = useService("rpc");

        // Ajouter un gestionnaire pour le bouton
        document.addEventListener("click", async (event) => {
            if (event.target.classList.contains("capture_position_btn")) {
                const recordId = env.model.root.id; // Obtenez l'ID de l'enregistrement
                if (!recordId) {
                    notification.add("Impossible d'obtenir l'identifiant de l'enregistrement.", { type: "danger" });
                    return;
                }
                try {
                    // Appel à la fonction pour capturer la position géographique
                    await capturePosition(notification, rpc, recordId);
                } catch (error) {
                    notification.add("Une erreur est survenue lors de la capture de la position.", { type: "danger" });
                    console.error(error);
                }
            }
        });
    },
};

registry.category("actions").add("capture_geo_position", captureGeoPositionButton);
