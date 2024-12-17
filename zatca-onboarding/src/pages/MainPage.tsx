import { useAppSelector } from "@/app/hooks";
import CustomModal from "@/components/CustomModal";
import { AnimatePresence, motion } from "framer-motion";
import Commission from "./Commision";
import Phases from "./Phases";
import Step1 from "./Steps/Step1";
import Tutorial from "./Tutorial";

const MainPage = () => {
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);

  const pages = [
    {
      id: 1,
      name: "Tutorial",
      component: <Tutorial />,
    },
    {
      id: 2,
      name: "Phases",
      component: <Phases />,
    },
    {
      id: 3,
      name: "Commercial Info",
      component: <Commission />,
    },
    {
      id: 4,
      name: "Company Info",
      component: <Step1 />,
    },
  ];

  return (
    <CustomModal>
      <AnimatePresence mode="wait">
        {pages
          .filter((page) => page.id === currentPage)
          .map((page) => (
            <motion.div
              key={page.id} // Unique key for Framer Motion to animate on changes
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.2 }}
              className="w-full h-full flex flex-col"
            >
              {page.component}
            </motion.div>
          ))}
      </AnimatePresence>
    </CustomModal>
  );
};

export default MainPage;
