// user.js

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// --- Element Selectors ---
const usersTab = document.getElementById("usersTab");
const clubTab = document.getElementById("clubTab");
const attendanceTab = document.getElementById("attendanceTab");
const scanTab = document.getElementById("scanTab");
const logoutTab = document.getElementById("logoutTab");

const employeesSection = document.getElementById("employeesSection");
const clubSection = document.getElementById("clubSection");

const userRows = document.getElementById("userRows");
const clubCards = document.getElementById("clubCards");

const clubModal = document.getElementById("clubModal");
const closeClubModal = document.getElementById("closeClubModal");
const clubNameDisplay = document.getElementById("clubNameDisplay");

// --- State Variables ---
let activeClubId = null;
let activeClubName = null;

// --- Section Switching Logic ---
function showSection(sectionToShow) {
  if (employeesSection) employeesSection.style.display = "none";
  if (clubSection) clubSection.style.display = "none";
  if (sectionToShow) {
    sectionToShow.style.display = "flex";
    sectionToShow.classList.remove("hidden");
  }
}

function setActiveTab(activeTab) {
  document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("nav-active"));
  if (activeTab) activeTab.classList.add("nav-active");
}

// --- Initial Setup ---
if (usersTab) {
  setActiveTab(usersTab);
  showSection(employeesSection);
  fetchUsers();
}

document.addEventListener("DOMContentLoaded", () => {
  const clubId = getCookie("club_id");
  if (scanTab) {
    if (!clubId || clubId === "None" || clubId === "null") {
      scanTab.style.display = "none";
    } else {
      scanTab.style.display = "block";
    }
  }
});

// --- User Management Functions ---
async function fetchUsers() {
  if (!userRows) return;
  userRows.innerHTML = `<p class="text-center text-slate-400 py-4">Loading users...</p>`;
  try {
    const res = await fetch("/employees/");
    const data = await res.json();
    const defaultProfileIcon = "/static/images/profile_icon.png";

    if (res.ok && data.employees && data.employees.length > 0) {
      userRows.innerHTML = "";
      data.employees.forEach(emp => {
        const row = document.createElement("div");
        row.className = "flex items-center bg-white/[0.03] rounded-3xl border border-white/10 px-4 py-2 hover:bg-white/5 transition-all text-white";
        const imageSrc = emp.image_path ? `/uploads/${emp.image_path}` : defaultProfileIcon;
        row.innerHTML = `
          <div class="w-16 font-mono text-blue-300">${emp.id}</div>
          <div class="flex-1"><p class="text-lg font-bold text-white">${emp.name}</p></div>
          <div class="w-48 text-center"><span class="text-emerald-400 font-black uppercase tracking-widest text-sm">${emp.member_code || "-"}</span></div>
          <div class="w-12 h-12 flex-shrink-0 rounded-full overflow-hidden mx-auto border-2 border-blue-400 shadow-md">
            <img src="${imageSrc}" alt="profile" class="w-full h-full object-cover">
          </div>
        `;
        userRows.appendChild(row);
      });
    } else {
      userRows.innerHTML = `<p class="text-center text-slate-400 py-4">No users found.</p>`;
    }
  } catch (err) {
    userRows.innerHTML = `<p class="text-center text-red-500 py-4">Error connecting to server.</p>`;
  }
}

// --- Club Management Functions ---
async function fetchClubs() {
  if (!clubCards) return;
  clubCards.innerHTML = `<p class="text-center text-slate-400 py-4">Loading clubs...</p>`;
  try {
    const res = await fetch("/clubs/");
    const data = await res.json();
    console.log(data);
    if (res.ok && data.clubs && data.clubs.length > 0) {
      clubCards.innerHTML = "";
      data.clubs.forEach(club => {
        const card = createClubCard(club);
        clubCards.appendChild(card);
      });
    } else {
      clubCards.innerHTML = `<p class="text-center text-slate-400 py-4">No clubs found.</p>`;
    }
  } catch (err) {
    clubCards.innerHTML = `<p class="text-center text-red-500 py-4">Error fetching clubs.</p>`;
  }
}

function createClubCard(club) {
  const card = document.createElement("div");
  card.className = "club-card glass-panel p-2 rounded-3xl cursor-pointer hover:bg-white/5 transition flex flex-col justify-between";
  card.dataset.id = club.id;
  card.innerHTML = `
    <div class="flex justify-between items-center club-content">
      <div class="mx-2 px-1 flex flex-col gap-1 w-full">
        <p class="club-code text-slate-300 text-sm">${club.club_code}</p>
        <div class="flex px-1 w-full items-center justify-between">
          <h3 class="club-name text-xl font-bold text-white">${club.club_name}</h3>
          <div class="">
            <button
              class="club-url p-1 mr-10
                    rounded-md
                    bg-white/10 backdrop-blur
                    text-white text-xs truncate
                    border border-white/10
                    hover:bg-blue-500/20 hover:text-blue-200
                    hover:border-blue-400/30
                    transition-all duration-200 ease-out
                    active:scale-95"
              title="Copy URL"
              data-url="${club.url}"
            >
              ${club.url}
            </button>

          </div>
        </div>
      </div>
    </div>
  `;

  // Copy URL handler (for text + button)
  card.querySelectorAll(".club-url").forEach(el => {
    el.addEventListener("click", e => {
      e.stopPropagation();

      const url = el.dataset.url;
      navigator.clipboard.writeText(url);

      // Optional quick feedback
      el.classList.add("text-green-400");
      setTimeout(() => el.classList.remove("text-green-400"), 600);
    });
  });

  return card;
}

// --- Event Listeners ---
if (usersTab) {
  usersTab.addEventListener("click", () => {
    setActiveTab(usersTab);
    showSection(employeesSection);
    fetchUsers();
  });
}

if (clubTab) {
  clubTab.addEventListener("click", () => {
    setActiveTab(clubTab);
    showSection(clubSection);
    fetchClubs();
  });
}

if (attendanceTab) {
  attendanceTab.addEventListener("click", () => { window.location.href = "/attendance"; });
}

if (scanTab) {
  scanTab.addEventListener("click", () => { window.location.href = "/scan"; });
}

if (logoutTab) {
  logoutTab.addEventListener("click", () => { window.location.href = "/logout"; });
}

// --- Modal Handlers ---
if (clubCards) {
  clubCards.addEventListener("click", async e => {
    const card = e.target.closest(".club-card");
    if (!card) return;
    activeClubId = card.dataset.id;
    activeClubName = card.querySelector(".club-name").innerText;
    if (clubNameDisplay) clubNameDisplay.innerText = activeClubName;
    if (clubModal) clubModal.classList.remove("hidden");
    loadUsersForClub(activeClubId);
  });
}

if (closeClubModal) {
  closeClubModal.onclick = () => { if (clubModal) clubModal.classList.add("hidden"); };
}

async function loadUsersForClub(clubId) {
  if (!clubModal) return;
  const container = clubModal.querySelector(".overflow-y-auto");
  if (!container) return;
  container.innerHTML = `<p class="text-slate-400 text-center py-4">Loading users...</p>`;
  try {
    const res = await fetch(`/clubs/${clubId}/users`);
    const data = await res.json();
    if (!res.ok || !data.users || data.users.length === 0) {
      container.innerHTML = `<p class="text-slate-400 text-center py-4">No users assigned</p>`;
      return;
    }
    container.innerHTML = "";
    data.users.forEach(user => {
      container.appendChild(createUserCard(user));
    });
  } catch {
    container.innerHTML = `<p class="text-red-400 text-center py-4">Failed to load users</p>`;
  }
}

function createUserCard(user) {
  const card = document.createElement("div");
  card.className = "user-card flex justify-between items-start bg-blue-900/40 p-4 rounded-xl border border-blue-700/30";
  card.dataset.id = user.id;
  card.innerHTML = `
    <div class="flex flex-col gap-2 w-full user-fields">
      ${field("Name", user.name)}
      ${field("Username", user.username)}
      ${field("Password", "••••••••")}
      ${field("Mobile", user.mobile)}
    </div>
  `;
  return card;
}

function field(label, value) {
  return `
    <div class="flex flex-col">
      <label class="text-slate-400 text-xs uppercase">${label}</label>
      <span class="text-white text-sm">${value}</span>
    </div>
  `;
}