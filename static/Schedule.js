async function loadSchedule() {
    try {
        const res = await fetch("/api/schedule");
        const data = await res.json();
        if (!res.ok) {
            throw new Error("Failed to fetch schedule");
        }

        console.log("Schedule data:", data); // debug

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

    } catch (error) {
        console.error("Error loading schedule:", error);
    }
}

window.onload = loadSchedule;