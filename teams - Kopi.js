function hexToRGBA(hex, alpha = 0.75) {
    if (!hex || !hex.startsWith("#")) return `rgba(255,255,255,${alpha})`;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

async function loadTeams() {
    try {
        const response = await fetch("http://127.0.0.1:5000/results");
        const drivers = await response.json();
        const container = document.getElementById("teams-container");
        container.innerHTML = "";

        const teamColors = {
            "Mercedes": "#00D2BE",
            "Red Bull Racing": "#1E41FF",
            "Ferrari": "#DC0000",
            "McLaren": "#FF8700",
            "Alpine": "#00A1E8",
            "Aston Martin": "#006F62",
            "Alfa Romeo": "#900000",
            "Haas F1 Team": "#E6002B",
            "AlphaTauri": "#2B4562",
            "Williams": "#005AFF",
            "Kick Sauber": "#01C00E",
            "Racing Bulls": "#6C98FF"
        };

        // Group drivers by team
        const teamsMap = {};
        drivers.forEach(driver => {
            const team = driver.TeamName;
            if (!teamsMap[team]) teamsMap[team] = [];
            teamsMap[team].push(driver);
        });

        for (const [teamName, teamDrivers] of Object.entries(teamsMap)) {
            const card = document.createElement("div");
            card.className = "team-card";

            const color = teamColors[teamName] ?? "#888";
            card.style.background = color;
            card.style.setProperty("--team-shadow", `0 10px 20px ${hexToRGBA(color)}`);

            const driverList = teamDrivers
                .map(d => `${d.Abbreviation}: Position ${d.Position}`)
                .join("<br>");

            card.innerHTML = `
                <h3>${teamName}</h3>
                <p>${driverList}</p>
            `;

            container.appendChild(card);
        }

    } catch (error) {
        console.error("Error loading teams:", error);
    }
}

document.addEventListener("DOMContentLoaded", loadTeams);