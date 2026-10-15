document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const teacherStatus = document.getElementById("teacher-status");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;
  let messageTimeout;

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    clearTimeout(messageTimeout);
    messageTimeout = setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function updateTeacherUI(username) {
    isTeacher = Boolean(username);
    signupContainer.hidden = !isTeacher;
    loginButton.classList.toggle("hidden", isTeacher);
    teacherStatus.textContent = isTeacher ? `Signed in as ${username}` : "";
    teacherStatus.classList.toggle("hidden", !isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
  }

  async function readResponse(response) {
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "An error occurred");
    }
    return result;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await readResponse(response);
      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft =
          details.max_participants - details.participants.length;
        const title = document.createElement("h4");
        title.textContent = name;
        activityCard.appendChild(title);
        activityCard.appendChild(createParagraph(details.description));
        activityCard.appendChild(
          createParagraph(`Schedule: ${details.schedule}`, "Schedule:")
        );
        activityCard.appendChild(
          createParagraph(`Availability: ${spotsLeft} spots left`, "Availability:")
        );
        activityCard.appendChild(createParticipants(name, details.participants));
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.textContent = "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  function createParagraph(text, boldPrefix) {
    const paragraph = document.createElement("p");
    if (boldPrefix) {
      const label = document.createElement("strong");
      label.textContent = boldPrefix;
      paragraph.append(label, text.slice(boldPrefix.length));
    } else {
      paragraph.textContent = text;
    }
    return paragraph;
  }

  function createParticipants(activity, participants) {
    const container = document.createElement("div");
    container.className = "participants-container";
    if (participants.length === 0) {
      const emptyMessage = document.createElement("p");
      const emphasis = document.createElement("em");
      emphasis.textContent = "No participants yet";
      emptyMessage.appendChild(emphasis);
      container.appendChild(emptyMessage);
      return container;
    }

    const heading = document.createElement("h5");
    heading.textContent = "Participants:";
    container.appendChild(heading);
    const list = document.createElement("ul");
    list.className = "participants-list";
    participants.forEach((email) => {
      const item = document.createElement("li");
      const address = document.createElement("span");
      address.className = "participant-email";
      address.textContent = email;
      item.appendChild(address);
      if (isTeacher) {
        const button = document.createElement("button");
        button.className = "delete-btn";
        button.type = "button";
        button.textContent = "Unregister";
        button.dataset.activity = activity;
        button.dataset.email = email;
        button.setAttribute("aria-label", `Unregister ${email} from ${activity}`);
        item.appendChild(button);
      }
      list.appendChild(item);
    });
    container.appendChild(list);
    return container;
  }

  async function handleUnregister(event) {
    const button = event.target.closest(".delete-btn");
    if (!button) {
      return;
    }
    const { activity, email } = button.dataset;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );
      const result = await readResponse(response);
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      console.error("Error unregistering:", error);
      showMessage(error.message, "error");
    }
  }

  activitiesList.addEventListener("click", handleUnregister);

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );
      const result = await readResponse(response);
      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      console.error("Error signing up:", error);
      showMessage(error.message, "error");
    }
  });

  loginButton.addEventListener("click", () => {
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");
    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await readResponse(response);
      loginForm.reset();
      loginDialog.close();
      updateTeacherUI(result.username);
      await fetchActivities();
    } catch (error) {
      loginError.textContent = error.message;
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      await readResponse(response);
      updateTeacherUI(null);
      await fetchActivities();
    } catch (error) {
      console.error("Error logging out:", error);
      showMessage(error.message, "error");
    }
  });

  async function initialize() {
    try {
      const response = await fetch("/auth/me");
      const result = await readResponse(response);
      updateTeacherUI(result.authenticated ? result.username : null);
    } catch (error) {
      console.error("Error checking teacher session:", error);
      updateTeacherUI(null);
    }
    await fetchActivities();
  }

  initialize();
});
