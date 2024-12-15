import RegistirationForm from "@/components/RegistirationForm";
import Step1 from "@/pages/Steps/Step1";
import { forwardRef, useEffect, useRef } from "react";
import Commision from "./Commision";
import Phases from "./Phases";
import Step2 from "./Steps/Step2";
import Step3 from "./Steps/Step3";
import Tutorial from "./Tutorial";

const Welcome = forwardRef<HTMLDivElement>((_, ref) => {
  const tutorialPageRef = useRef<HTMLDialogElement>(null);
  const phasesPageRef = useRef<HTMLDialogElement>(null);
  const commisionPageRef = useRef<HTMLDialogElement>(null);
  const registerForm = useRef<HTMLDialogElement>(null);

  const handleTutorialClick = () => {
    tutorialPageRef.current?.close();
    phasesPageRef.current?.showModal();
  };

  const handlePhasesBack = () => {
    phasesPageRef.current?.close();
    tutorialPageRef.current?.showModal();
  };

  const handlePhaseSubmit = (phase: string) => {
    sessionStorage.setItem("phase", phase);
    phasesPageRef.current?.close();
    commisionPageRef.current?.showModal();
  };

  const handleCommisionBack = () => {
    commisionPageRef.current?.close();
    phasesPageRef.current?.showModal();
  };

  const handleCommissionSubmit = () => {
    commisionPageRef.current?.close();
    registerForm.current?.showModal();
  };
  const handleRegistirationBack = () => {
    registerForm.current?.close();
    commisionPageRef.current?.showModal();
  };

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        console.log("Fetching");
        const res = await frappe.db.get_doc("User", "Guest");
        console.log(res);
      } catch (Err) {
        console.log(Err);
      }
    };
    fetchUsers();
  }, []);

  return (
    <div
      ref={ref}
      className="relative h-screen bg-cover object-cover bg-center bg-no-repeat"
    >
      <img
        className="bg-cover bg-center h-full w-full"
        src={`${
          isDev
            ? "Welcome.png"
            : "/assets/optima_zatca/zatca-onboarding/Welcome.png"
        }`}
      />
      <button
        onClick={() => tutorialPageRef.current?.showModal()}
        className="absolute font-bold text-3xl top-[71%] left-[10%] rounded-md w-[263px] h-[78px] bg-[#ffcd5e]"
      >
        Get Started
      </button>
      <Tutorial
        ref={tutorialPageRef}
        handleTutorialClick={handleTutorialClick}
      />
      <Phases
        ref={phasesPageRef}
        handlePhasesBack={handlePhasesBack}
        handlePhaseSubmit={handlePhaseSubmit}
      />
      <Commision
        ref={commisionPageRef}
        handleCommisionBack={handleCommisionBack}
        handleCommissionSubmit={handleCommissionSubmit}
      />

      <RegistirationForm
        ref={registerForm}
        img="./data.svg"
        handleRegistirationBack={handleRegistirationBack}
      >
        <Step1 />
        <Step2 />
        <Step3 />
      </RegistirationForm>
    </div>
  );
});

export default Welcome;
