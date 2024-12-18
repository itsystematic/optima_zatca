import { useAppDispatch } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { Card, Flex, Image, Typography } from "antd";

const Phases = () => {
  const dispatch = useAppDispatch();

  interface Phases {
    id: number;
    img: string;
    name: string;
  }

  const phases: Phases[] = [
    {
      img: !isDev ? "/assets/optima_zatca/zatca-onboarding/Phase_1.svg" : "Phase_1.svg",
      id: 1,
      name: "المرحلة الاولة",
    },
    {
      img: !isDev ? "/assets/optima_zatca/zatca-onboarding/Phase_2.svg" : "Phase_2.svg",
      id: 2,
      name: "المرحلة الثانية",
    },
  ];

  const handlePhaseSelect = (phase: number) => {
    console.log(phase);
    dispatch(setCurrentPage(3));
  };

  return (
      <Flex gap={16} flex={1} justify="center" align="center">
        {phases.map((phase) => (
          <Card
            onClick={() => handlePhaseSelect(phase.id)}
            key={phase.id}
            hoverable
            className="transition-all group bg-[#2a2439] text-white duration-300 w-[180px] h-[180px] flex justify-center items-center rounded-3xl hover:bg-white cursor-pointer hover:text-white border-none"
          >
            <div className="flex justify-center items-center flex-col gap-5">
              <Image
                preview={false}
                width={120}
                src={phase.img}
                alt="Expressive Image"
                className=" transition-all duration-300"
              />

              <Typography.Text className="text-xl font-medium text-white group-hover:text-black">
                {phase.name}
              </Typography.Text>
            </div>
          </Card>
        ))}
      </Flex>
  );
};

export default Phases;
