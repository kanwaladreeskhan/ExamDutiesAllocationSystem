document.addEventListener("DOMContentLoaded", () => {
    const alertEl = document.getElementById("socket-alert");
    const messageEl = document.getElementById("socket-message");

    // Exit early if required elements are missing
    if (!alertEl || !messageEl) {
        console.warn("[WebSocket] Required DOM elements not found.");
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const socketUrl = `${protocol}${window.location.host}/ws/notifications/`;
    const socket = new WebSocket(socketUrl);

    socket.addEventListener("open", () => {
        console.log("[WebSocket] Connected successfully");
    });

    socket.addEventListener("message", (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.type === "duty_update") {
                messageEl.textContent = data.message || "Your exam duty roster has been updated.";
                alertEl.classList.remove("d-none");
                alertEl.classList.add("show");
            }
        } catch (error) {
            console.error("[WebSocket] Invalid notification message:", error);
        }
    });

    socket.addEventListener("error", (error) => {
        console.warn("[WebSocket] Connection error:", error);
    });

    socket.addEventListener("close", (event) => {
        console.log(`[WebSocket] Connection closed (code: ${event.code})`);
    });
});