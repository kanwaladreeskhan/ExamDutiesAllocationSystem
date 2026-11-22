document.addEventListener("DOMContentLoaded", () => {
    const alertEl = document.getElementById("socket-alert");
    const messageEl = document.getElementById("socket-message");

    if (!alertEl || !messageEl) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const socket = new WebSocket(`${protocol}${window.location.host}/ws/notifications/`);

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
            console.error("Invalid notification message:", error);
        }
    });

    socket.addEventListener("error", (error) => {
        console.warn("Notification connection failed.", error);
    });
});