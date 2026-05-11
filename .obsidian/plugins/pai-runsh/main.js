/*
 * PAI RunSH v1.2.0
 * Enhanced fork of obsidian-runsh with inline output capture.
 * Runs via zsh login shell to inherit user's full PATH and env.
 * Original: https://github.com/Deedone/obsidian-runsh
 */

const { Plugin } = require("obsidian");
const { spawn } = require("child_process");

module.exports = class PaiRunsh extends Plugin {
  async onload() {
    this.registerMarkdownCodeBlockProcessor("runsh", (source, el, _ctx) => {
      this.processRunshBlock(source, el);
    });
  }

  processRunshBlock(source, el) {
    const parts = source.split("%%%");
    const cmd = parts[0].trim();
    if (!cmd) return;

    const buttonText =
      parts.length > 1 ? parts.slice(1).join("%%%").trim() : "▶ Run";

    const wrapper = el.createDiv({ cls: "pai-runsh-block" });
    const header = wrapper.createDiv({ cls: "pai-runsh-header" });

    const button = header.createEl("button", {
      text: buttonText || "▶ Run",
      cls: "pai-runsh-button",
    });
    button.title = cmd;

    const clearBtn = header.createEl("button", {
      text: "✕",
      cls: "pai-runsh-clear",
    });
    clearBtn.hide();

    const output = wrapper.createDiv({ cls: "pai-runsh-output" });
    output.hide();

    let running = false;

    button.addEventListener("click", async () => {
      if (running) return;
      running = true;

      const originalText = button.textContent || buttonText;
      button.setText("⏳ Running…");
      button.disabled = true;
      output.show();
      output.setText("");
      output.removeClass("pai-runsh-error");
      clearBtn.hide();

      try {
        const result = await runCommand(cmd);
        const outputLines = [];

        if (result.stdout.trim()) outputLines.push(result.stdout.trimEnd());
        if (result.stderr.trim()) outputLines.push(result.stderr.trimEnd());

        const text = outputLines.join("\n");

        if (text) {
          output.setText(text);
          if (result.code !== 0 && !result.stdout.trim()) {
            output.addClass("pai-runsh-error");
          }
        } else if (result.code !== 0) {
          output.setText(`✕ Exit code ${result.code}`);
          output.addClass("pai-runsh-error");
        } else {
          output.setText("✓ Done");
        }
      } catch (e) {
        output.setText(`✕ ${e.message}`);
        output.addClass("pai-runsh-error");
      } finally {
        button.setText(originalText);
        button.disabled = false;
        clearBtn.show();
        running = false;
      }
    });

    clearBtn.addEventListener("click", () => {
      output.setText("");
      output.hide();
      clearBtn.hide();
      output.removeClass("pai-runsh-error");
    });
  }
};

function runCommand(cmd) {
  return new Promise((resolve, reject) => {
    const child = spawn("zsh", ["-l", "-c", cmd], {
      timeout: 120000,
      maxBuffer: 2 * 1024 * 1024,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error("Command timed out after 120s"));
    }, 120000);

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    child.on("close", (code) => {
      clearTimeout(timeout);
      resolve({ stdout, stderr, code });
    });

    child.on("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}
