import './style.css'

import {Application, Assets, Graphics, Sprite} from 'pixi.js';

import typescriptLogo from './typescript.svg'
import viteLogo from '/vite.svg'
import {setupCounter} from './counter.ts'

// document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
//   <div>
//     <a href="https://vite.dev" target="_blank">
//       <img src="${viteLogo}" class="logo" alt="Vite logo" />
//     </a>
//     <a href="https://www.typescriptlang.org/" target="_blank">
//       <img src="${typescriptLogo}" class="logo vanilla" alt="TypeScript logo" />
//     </a>
//     <h1>Vite + TypeScript</h1>
//     <div class="card">
//       <button id="counter" type="button"></button>
//     </div>
//     <p class="read-the-docs">
//       Click on the Vite and TypeScript logos to learn more
//     </p>
//   </div>
// `
//
// setupCounter(document.querySelector<HTMLButtonElement>('#counter')!)

const test = 'lmao';

async function setupApp() {
    const app = new Application();
    await app.init({width: 640, height: 360, antialias: false});
    document.body.appendChild(app.canvas);

    await Assets.load('https://pixijs.com/assets/bunny.png');
    let sprite = Sprite.from('https://pixijs.com/assets/bunny.png');

    console.log(test);

    app.stage.addChild(sprite);

    let scale = 1;
    sprite.scale = scale;
    sprite.eventMode = 'dynamic';

    sprite.on('pointerdown', (event) => {
        scale += .1;
        console.log(scale);
        sprite.scale = scale;
    });

    for (let i = 0; i < 5; i++) {
        let circle = new Graphics()
            .circle(100 + i * 120, 100, 50)
            .fill('red');
        app.stage.addChild(circle)
    }

    let elapsed = 0.0;
    // Tell our application's ticker to run a new callback every frame, passing
    // in the amount of time that has passed since the last tick
    app.ticker.add((ticker) => {
        // Add the time to our total elapsed time
        elapsed += ticker.deltaTime;
        // Update the sprite's X position based on the cosine of our elapsed time.  We divide
        // by 50 to slow the animation down a bit...
        // sprite.x = 100.0 + Math.cos(elapsed / 50.0) * 100.0;

        // while (app.stage.children[0]) {
        //     app.stage.removeChild(app.stage.children[0])
        // }
        // sprite = Sprite.from('https://pixijs.com/assets/bunny.png');
        // app.stage.addChild(sprite);

        sprite.x = 100.0 + Math.cos(elapsed / 50.0) * 100.0;


    });

    // app.stage.destroy()
}

await setupApp()