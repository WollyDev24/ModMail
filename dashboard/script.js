// =====================
// Helpers
// =====================
async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

// =====================
// Load Dashboard Data
// =====================
async function loadDashboard() {
  try {
    const info = await fetchJSON("/api/info");
    const tickets = await fetchJSON("/api/tickets");

    // Update overview stats
    document.getElementById("guildCount").textContent = info.guilds;
    document.getElementById("ticketCount").textContent = info.open_tickets;
    document.getElementById("userCount").textContent = info.users;
    document.getElementById("uptime").textContent = info.uptime;

    // Update tickets list
    const ticketList = document.getElementById("ticketList");
    ticketList.innerHTML = "";
    tickets.forEach(t => {
      const div = document.createElement("div");
      div.className = "item";
      div.innerHTML = `<strong>${t.user}</strong> — <small>${t.channel}</small>`;
      ticketList.appendChild(div);
    });

    // Update logs (show last 5 logs)
    const logList = document.getElementById("logList");
    logList.innerHTML = "";
    for (let t of tickets) {
      const logs = await fetchJSON(`/api/logs/${t.id}`);
      logs.logs.slice(-5).forEach(l => {
        const div = document.createElement("div");
        div.className = "item";
        div.textContent = `[${t.user}] ${l}`;
        logList.appendChild(div);
      });
    }

    // Update chart (Tickets per Day) dynamically
    const chartLabels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
    const chartData = chartLabels.map(() => Math.floor(Math.random() * 10)); // Demo random
    updateChart(chartLabels, chartData);

  } catch (err) {
    console.error("Error loading dashboard:", err);
  }
}

// =====================
// Chart.js
// =====================
let ticketChart;
function updateChart(labels, data) {
  const ctx = document.getElementById("chart").getContext("2d");
  if (ticketChart) {
    ticketChart.data.labels = labels;
    ticketChart.data.datasets[0].data = data;
    ticketChart.update();
    return;
  }
  ticketChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Tickets per Day",
        data: data,
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.2)",
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e6edf3" } } },
      scales: {
        x: { ticks: { color: "#8b949e" } },
        y: { ticks: { color: "#8b949e" } }
      }
    }
  });
}

// =====================
// Auto-refresh
// =====================
loadDashboard();
setInterval(loadDashboard, 5000); // refresh every 5 seconds
