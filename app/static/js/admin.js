// admin.js

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// --- Element Selectors (Top Level) ---
const usersTab = document.getElementById("usersTab");
const clubTab = document.getElementById("clubTab");
const attendanceTab = document.getElementById("attendanceTab");
const scanTab = document.getElementById("scanTab");
const punchTab = document.getElementById("punchTab");
const logoutTab = document.getElementById("logoutTab");

const employeesSection = document.getElementById("employeesSection");
const clubSection = document.getElementById("clubSection");

const addUserBtn = document.getElementById("addUserBtn");
const userRows = document.getElementById("userRows");

const clubCards = document.getElementById("clubCards");
const addClubBtn = document.getElementById("addClubBtn");
const addClubModal = document.getElementById("addClubModal");
const closeAddClubModal = document.getElementById("closeAddClubModal");
const clubModalActions = document.getElementById("clubModalActions");
const newClubNameInput = document.getElementById("newClubName");
const newClubCodeInput = document.getElementById("newClubCode");
const clubModalTitle = document.getElementById("clubModalTitle");

const clubModal = document.getElementById("clubModal");
const closeClubModal = document.getElementById("closeClubModal");
const clubNameDisplay = document.getElementById("clubNameDisplay");
const addUserToClubBtn = document.getElementById("addUserToClub");

// --- Pagination Elements ---
const prevPageBtn = document.getElementById("prevPage");
const nextPageBtn = document.getElementById("nextPage");
const currentPageNumDisplay = document.getElementById("currentPageNum");
const totalPageNumDisplay = document.getElementById("totalPageNum");

// --- State Variables ---
let activeClubId = null;
let activeClubName = null;
let editingClubId = null;

// --- Pagination State ---
let currentPage = 1;
const pageSize = 7;
let totalEmployees = 0;

// --- Section Switching Logic ---
function showSection(targetSection) {
  console.log("Switching to section:", targetSection ? targetSection.id : "null");
  const sections = [employeesSection, clubSection];
  sections.forEach(s => {
    if (s) {
      s.classList.add("hidden");
      s.style.display = "none";
    }
  });

  if (targetSection) {
    targetSection.classList.remove("hidden");
    targetSection.style.display = "flex";
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
  currentPage = 1;
  fetchUsers(currentPage);
}

document.addEventListener("DOMContentLoaded", () => {
  const initialClubId = getCookie("club_id");
  console.log("Initial club_id from cookie:", initialClubId);
  if (scanTab) {
    if (!initialClubId || initialClubId === "None" || initialClubId === "null") {
      scanTab.style.display = "none";
    } else {
      scanTab.style.display = "block";
    }
  }
});

// --- User Management Functions ---
async function fetchUsers(page = 1) {
  if (!userRows) return;
  userRows.innerHTML = `<p class="text-center text-slate-400 py-4">Loading users...</p>`;
  try {
    const res = await fetch(`/employees?page=${page}&size=${pageSize}`);
    const data = await res.json();
    const defaultProfileIcon = "/static/images/profile_icon.png";

    if (res.ok && data.employees && data.employees.length > 0) {
      userRows.innerHTML = "";
      totalEmployees = data.total;
      currentPage = data.page;

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
      updatePaginationUI();
    } else {
      userRows.innerHTML = `<p class="text-center text-slate-400 py-4">No users found.</p>`;
      totalEmployees = 0;
      updatePaginationUI();
    }
  } catch (err) {
    userRows.innerHTML = `<p class="text-center text-red-500 py-4">Error connecting to server.</p>`;
    console.error("fetchUsers error:", err);
  }
}

function updatePaginationUI() {
  const totalPages = Math.ceil(totalEmployees / pageSize) || 1;

  if (currentPageNumDisplay) currentPageNumDisplay.innerText = currentPage;
  if (totalPageNumDisplay) totalPageNumDisplay.innerText = totalPages;

  if (prevPageBtn) prevPageBtn.disabled = (currentPage <= 1);
  if (nextPageBtn) nextPageBtn.disabled = (currentPage >= totalPages);
}

// --- Club Management Functions ---
async function fetchClubs() {
  if (!clubCards) return;
  clubCards.innerHTML = `<p class="text-center text-slate-400 py-4">Loading clubs...</p>`;
  try {
    const res = await fetch("/clubs");
    const data = await res.json();

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
    console.error("fetchClubs error:", err);
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
      <div class="flex px-1 mx-2 gap-4">
        <button class="editClub text-green-400 hover:text-blue-300 transition-all text-lg font-bold" title="Edit">✎</button>
        <button class="deleteClub text-red-400 hover:text-red-500 transition-all text-lg font-bold" title="Delete">🗑️</button>
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
    currentPage = 1;
    fetchUsers(currentPage);
  });
}

if (clubTab) {
  clubTab.addEventListener("click", () => {
    console.log("Club tab clicked");
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

if (addUserBtn) {
  addUserBtn.addEventListener("click", () => { window.location.href = "/employee_upload/"; });
}

// --- Pagination Listeners ---
if (prevPageBtn) {
  prevPageBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      fetchUsers(currentPage - 1);
    }
  });
}

if (nextPageBtn) {
  nextPageBtn.addEventListener("click", () => {
    const totalPages = Math.ceil(totalEmployees / pageSize);
    if (currentPage < totalPages) {
      fetchUsers(currentPage + 1);
    }
  });
}

if (addUserToClubBtn) {
  addUserToClubBtn.addEventListener("click", () => { window.location.href = "/signup"; });
}

// --- Modal Handlers ---

if (addClubBtn) {
  addClubBtn.addEventListener("click", () => {
    editingClubId = null;
    if (clubModalTitle) clubModalTitle.innerText = "Add New Club";
    if (newClubNameInput) newClubNameInput.value = "";
    if (newClubCodeInput) newClubCodeInput.value = "";
    if (clubModalActions) {
      clubModalActions.innerHTML = `<button id="addNewClubBtn" class="mt-2 bg-blue-500/10 border border-blue-400/30 px-4 py-2 rounded-xl text-blue-300 text-xs uppercase hover:bg-blue-400 hover:text-white transition-all">Add</button>`;
      document.getElementById("addNewClubBtn").onclick = handleAddClub;
    }
    if (addClubModal) addClubModal.classList.remove("hidden");
  });
}

if (closeAddClubModal) {
  closeAddClubModal.onclick = () => { if (addClubModal) addClubModal.classList.add("hidden"); };
}

async function handleAddClub() {
  const name = newClubNameInput.value.trim();
  const code = newClubCodeInput.value.trim();
  if (!name) return alert("Enter club name!");
  if (!code || !/^\d{18}$/.test(code)) return alert("Code must be 18 digits!");

  try {
    const res = await fetch("/clubs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ club_name: name, club_code: code })
    });
    const data = await res.json();
    if (res.ok) {
      fetchClubs();
      if (addClubModal) addClubModal.classList.add("hidden");
    } else {
      alert(data.MESSAGE || "Error adding club.");
    }
  } catch {
    alert("Server error.");
  }
}

// --- Club Card Interactivity ---

if (clubCards) {
  clubCards.addEventListener("click", async e => {
    const card = e.target.closest(".club-card");
    if (!card) return;
    const clubId = card.dataset.id;

    if (e.target.classList.contains("deleteClub")) {
      e.stopPropagation();
      if (!confirm("Delete this club?")) return;
      try {
        const res = await fetch(`/clubs/${clubId}`, { method: "DELETE" });
        if (res.ok) card.remove();
        else alert("Failed to delete club.");
      } catch (err) { alert("Server error."); }
      return;
    }

    if (e.target.classList.contains("editClub")) {
      e.stopPropagation();
      editingClubId = clubId;
      const name = card.querySelector(".club-name").innerText;
      const code = card.querySelector(".club-code").innerText;

      if (clubModalTitle) clubModalTitle.innerText = "Update Club";
      if (newClubNameInput) newClubNameInput.value = name;
      if (newClubCodeInput) newClubCodeInput.value = code;

      if (clubModalActions) {
        clubModalActions.innerHTML = `
          <button id="updateClubBtn" class="mt-2 bg-green-500/10 border border-green-400/30 px-4 py-2 rounded-xl text-green-300 text-xs uppercase hover:bg-green-400 hover:text-white transition-all">Update</button>
          <button id="cancelUpdateBtn" class="mt-2 bg-slate-500/10 border border-slate-400/30 px-4 py-2 rounded-xl text-slate-300 text-xs uppercase hover:bg-slate-400 hover:text-white transition-all">Cancel</button>
        `;
        document.getElementById("updateClubBtn").onclick = handleUpdateClub;
        document.getElementById("cancelUpdateBtn").onclick = () => { if (addClubModal) addClubModal.classList.add("hidden"); };
      }
      if (addClubModal) addClubModal.classList.remove("hidden");
      return;
    }

    // Default click - open club details
    activeClubId = clubId;
    activeClubName = card.querySelector(".club-name").innerText;
    if (clubNameDisplay) clubNameDisplay.innerText = activeClubName;
    if (clubModal) clubModal.classList.remove("hidden");
    loadUsersForClub(activeClubId);
  });
}

async function handleUpdateClub() {
  const name = newClubNameInput.value.trim();
  const code = newClubCodeInput.value.trim();
  if (!name) return alert("Enter club name!");
  if (!code || !/^\d{18}$/.test(code)) return alert("Code must be 18 digits!");

  try {
    const res = await fetch(`/clubs/${editingClubId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ club_name: name, club_code: code })
    });
    if (res.ok) {
      fetchClubs();
      if (addClubModal) addClubModal.classList.add("hidden");
    } else {
      alert("Update failed");
    }
  } catch {
    alert("Server error.");
  }
}

if (closeClubModal) {
  closeClubModal.onclick = () => { if (clubModal) clubModal.classList.add("hidden"); };
}

// --- User-in-Club Management ---

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
