async function loadSchedule() {
    try {
        const res = await fetch("/api/schedule/data");

        if (!res.ok) {
            throw new Error(`HTTP error: ${res.status}`);
        }

        const data = await res.json();

        const list = document.getElementById("schedule");
        list.innerHTML = "";

        data.forEach(event => {
            const li = document.createElement("li");

            li.innerHTML = `
                <strong>${event.name}</strong><br>
                ${event.country} - ${event.date}
            `;

            list.appendChild(li);
        });

    } catch (err) {
        console.error("Failed to load schedule:", err);
    }
}

window.addEventListener("DOMContentLoaded", loadSchedule);