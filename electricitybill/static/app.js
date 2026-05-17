let balanceChart;
let deltaChart;

function yuan(value) {
  return value === null || value === undefined ? "--" : `¥ ${Number(value).toFixed(2)}`;
}

function days(value) {
  return value === null || value === undefined ? "数据不足" : `${Number(value).toFixed(1)} 天`;
}

async function loadDashboard() {
  const [statusResponse, readingsResponse] = await Promise.all([
    fetch("/api/status"),
    fetch("/api/readings"),
  ]);
  const status = await statusResponse.json();
  const readings = await readingsResponse.json();
  const metrics = status.metrics;
  document.getElementById("currentBalance").textContent = yuan(metrics.current_balance);
  document.getElementById("consumption24h").textContent = yuan(metrics.last_24h_consumption);
  document.getElementById("average7d").textContent = yuan(metrics.avg_daily_consumption_7d);
  document.getElementById("daysRemaining").textContent = days(metrics.estimated_days_remaining);
  const message = document.getElementById("message");
  message.textContent = `状态：${status.last_query_status}；最后更新：${status.last_updated || "暂无"}`;
  message.classList.toggle("error", status.last_query_status === "auth_error");
  renderCharts(readings, metrics.deltas);
}

function renderCharts(readings, deltas) {
  const labels = readings.map((item) => new Date(item.recorded_at).toLocaleString());
  const balances = readings.map((item) => item.balance);
  const consumptions = deltas.map((item) => item.consumption ?? 0);
  if (balanceChart) balanceChart.destroy();
  if (deltaChart) deltaChart.destroy();
  balanceChart = new Chart(document.getElementById("balanceChart"), {
    type: "line",
    data: { labels, datasets: [{ label: "余额", data: balances, borderColor: "#f5a623", tension: 0.25 }] },
  });
  deltaChart = new Chart(document.getElementById("deltaChart"), {
    type: "bar",
    data: { labels, datasets: [{ label: "消耗/充值变化", data: consumptions, backgroundColor: "#60a5fa" }] },
  });
}

async function refreshNow() {
  const refreshButton = document.getElementById("refreshButton");
  const message = document.getElementById("message");
  refreshButton.disabled = true;
  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    if (!response.ok) {
      throw new Error(`刷新请求失败：${response.status}`);
    }
    await loadDashboard();
  } catch (error) {
    message.textContent = `刷新失败：${error.message}`;
    message.classList.add("error");
  } finally {
    refreshButton.disabled = false;
  }
}

document.getElementById("refreshButton").addEventListener("click", refreshNow);

loadDashboard().catch((error) => {
  const message = document.getElementById("message");
  message.textContent = `加载失败：${error.message}`;
  message.classList.add("error");
});
